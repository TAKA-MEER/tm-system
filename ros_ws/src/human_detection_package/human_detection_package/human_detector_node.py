import math
import struct

import numpy as np
from sklearn.cluster import DBSCAN

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan, PointCloud2, PointField
from std_msgs.msg import Header, Bool
import sensor_msgs_py.point_cloud2 as pc2

from tm_system_msgs.msg import HumanClusterList

# 安全停止：この距離（m）以内に何かあれば走行系を止める
SAFETY_STOP_DISTANCE = 0.8


class HumanDetectorNode(Node):
    """
    LiDAR (LaserScan) から人物の足クラスタを検出するノード。
    DBSCAN クラスタリング + 足サイズフィルタで人物候補を抽出し、
    HumanClusterList として出力する。
    """

    def __init__(self):
        super().__init__('human_detector')

        # DBSCANパラメータ: eps=近傍半径(m), min_samples=最小点数
        self.dbscan = DBSCAN(eps=0.15, min_samples=8)

        # 安全警告ログのスロットル用（最後に警告した時刻）
        self._last_safety_warn_time = 0.0

        self.sub = self.create_subscription(
            LaserScan, '/scan', self.callback, 10)
        self.pub = self.create_publisher(
            HumanClusterList, '/humans/detected', 10)
        # RViz 可視化用（色付き点群）
        self.pc_pub = self.create_publisher(
            PointCloud2, '/colored_points', 10)
        # 安全停止トピック（0.8m以内に障害物があれば True）
        self.safety_pub = self.create_publisher(
            Bool, '/safety/obstacle_near', 10)

        self.get_logger().info(
            f'HumanDetectorNode 起動完了（安全停止距離: {SAFETY_STOP_DISTANCE}m）')

    def callback(self, msg: LaserScan):
        # ──────────────────────────────────────
        # 1. 極座標 → 直交座標変換
        # ──────────────────────────────────────
        points = []
        angles = np.arange(msg.angle_min, msg.angle_max, msg.angle_increment)
        num_readings = min(len(angles), len(msg.ranges))

        for i in range(num_readings):
            r = msg.ranges[i]
            if msg.range_min < r < msg.range_max and not math.isnan(r) and not math.isinf(r):
                x = r * math.cos(angles[i])
                y = r * math.sin(angles[i])
                points.append([x, y])

        if len(points) == 0:
            return

        points_np = np.array(points)

        # ──────────────────────────────────────
        # 安全停止チェック：0.8m 以内に何かあれば即 True を発行
        # ──────────────────────────────────────
        distances = np.linalg.norm(points_np, axis=1)
        obstacle_near = bool(np.any(distances < SAFETY_STOP_DISTANCE))
        safety_msg = Bool()
        safety_msg.data = obstacle_near
        self.safety_pub.publish(safety_msg)
        if obstacle_near:
            # 1秒に1回だけ警告ログを出す（スパム防止）
            now_sec = self.get_clock().now().nanoseconds / 1e9
            if now_sec - self._last_safety_warn_time >= 1.0:
                self.get_logger().warn(
                    f'⚠️  安全停止: {SAFETY_STOP_DISTANCE}m以内に障害物検知 '
                    f'（最近傍: {float(np.min(distances)):.2f}m）'
                )
                self._last_safety_warn_time = now_sec

        # ──────────────────────────────────────
        # 2. DBSCAN クラスタリング
        # ──────────────────────────────────────
        labels = self.dbscan.fit_predict(points_np)
        unique_labels = set(labels)

        # ──────────────────────────────────────
        # 3. 足クラスタの抽出（幅 5cm〜20cm）
        # ──────────────────────────────────────
        leg_clusters = []   # 足クラスタ中心座標リスト
        leg_label_ids = []  # 対応するDBSCANラベル

        for label in unique_labels:
            if label == -1:  # ノイズ点
                continue
            cluster_pts = points_np[labels == label]
            if len(cluster_pts) < 3:
                continue

            max_pt = np.max(cluster_pts, axis=0)
            min_pt = np.min(cluster_pts, axis=0)
            width = np.linalg.norm(max_pt - min_pt)

            if 0.05 <= width <= 0.20:
                center = np.mean(cluster_pts, axis=0)
                leg_clusters.append(center)
                leg_label_ids.append(label)

        # ──────────────────────────────────────
        # 4. 足ペアリング → 人物候補生成
        # ──────────────────────────────────────
        people = []
        used = set()

        for i, ci in enumerate(leg_clusters):
            if i in used:
                continue
            used.add(i)
            person_centers = [ci]
            person_labels = [leg_label_ids[i]]

            # 0.5m 以内の別の足クラスタをペアとして探す
            best_j = -1
            min_d = 0.5
            for j, cj in enumerate(leg_clusters):
                if j in used:
                    continue
                d = np.linalg.norm(ci - cj)
                if d < min_d:
                    min_d = d
                    best_j = j

            if best_j != -1:
                used.add(best_j)
                person_centers.append(leg_clusters[best_j])
                person_labels.append(leg_label_ids[best_j])

            if len(person_centers) == 2:
                center = np.mean(person_centers, axis=0)
                people.append({
                    'center': center,
                    'labels': person_labels,
                })

        # ──────────────────────────────────────
        # 5. HumanClusterList メッセージを作成
        # ──────────────────────────────────────
        from geometry_msgs.msg import Point
        output = HumanClusterList()
        output.header = msg.header
        for p in people:
            pt = Point()
            pt.x = float(p['center'][0])
            pt.y = float(p['center'][1])
            pt.z = 0.0
            output.clusters.append(pt)
        self.pub.publish(output)

        # ──────────────────────────────────────
        # 6. RViz 用色付き点群の発行
        # ──────────────────────────────────────
        target_labels = set()
        for p in people:
            for lbl in p['labels']:
                target_labels.add(lbl)

        header = Header()
        header.stamp = msg.header.stamp
        header.frame_id = msg.header.frame_id

        fields = [
            PointField(name='x', offset=0, datatype=PointField.FLOAT32, count=1),
            PointField(name='y', offset=4, datatype=PointField.FLOAT32, count=1),
            PointField(name='z', offset=8, datatype=PointField.FLOAT32, count=1),
            PointField(name='rgb', offset=12, datatype=PointField.UINT32, count=1),
        ]

        pc2_points = []
        for idx, (px, py) in enumerate(points_np):
            label = labels[idx]
            if label in target_labels:
                r, g, b = 0, 255, 0    # 検出された人物：緑
            else:
                r, g, b = 255, 255, 255  # その他：白
            rgb = struct.unpack('I', struct.pack('BBBB', b, g, r, 255))[0]
            pc2_points.append([px, py, 0.0, rgb])

        pc2_msg = pc2.create_cloud(header, fields, pc2_points)
        self.pc_pub.publish(pc2_msg)


def main(args=None):
    rclpy.init(args=args)
    node = HumanDetectorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
