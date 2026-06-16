import numpy as np

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Vector3

from tm_system_msgs.msg import HumanClusterList, TrackedHuman, TrackedHumanList


class KalmanFilter2D:
    """
    2Dカルマンフィルタ。
    状態ベクトル: [x, y, vx, vy]
    """

    def __init__(self, dt: float = 0.1):
        self.x = np.zeros(4)
        self.F = np.array([
            [1, 0, dt, 0],
            [0, 1, 0, dt],
            [0, 0, 1, 0],
            [0, 0, 0, 1],
        ], dtype=float)
        self.H = np.array([
            [1, 0, 0, 0],
            [0, 1, 0, 0],
        ], dtype=float)
        self.P = np.eye(4) * 1.0
        self.Q = np.eye(4) * 0.01
        self.R = np.eye(2) * 0.1
        self.is_initialized = False

    def predict(self):
        if not self.is_initialized:
            return self.x
        self.x = self.F @ self.x
        self.P = self.F @ self.P @ self.F.T + self.Q
        return self.x

    def update(self, z: np.ndarray):
        if not self.is_initialized:
            self.x[0] = z[0]
            self.x[1] = z[1]
            self.is_initialized = True
            return self.x
        y = z - self.H @ self.x
        S = self.H @ self.P @ self.H.T + self.R
        K = self.P @ self.H.T @ np.linalg.inv(S)
        self.x = self.x + K @ y
        self.P = (np.eye(4) - K @ self.H) @ self.P
        return self.x


class TrackedEntry:
    """1人分の追跡状態を保持するクラス"""

    def __init__(self, human_id: int, init_pos: np.ndarray, dt: float = 0.1):
        self.id = human_id
        self.kf = KalmanFilter2D(dt=dt)
        self.kf.update(init_pos)
        self.miss_count = 0  # 観測できなかったフレーム数


class HumanTrackerNode(Node):
    """
    HumanClusterList を受け取り、フレーム間で ID を付けて追跡するノード。
    カルマンフィルタで各人物の位置・速度を推定し、TrackedHumanList を出力する。
    """

    def __init__(self):
        super().__init__('human_tracker')

        self._next_id = 0
        self._tracked: list[TrackedEntry] = []
        self._last_stamp = None

        # 2つの観測点が同一人物と判定される最大距離（m）
        self._assoc_threshold = 0.8
        # これ以上観測されなければ追跡を削除（フレーム数）
        self._max_miss = 10

        self.sub = self.create_subscription(
            HumanClusterList, '/humans/detected', self.callback, 10)
        self.pub = self.create_publisher(
            TrackedHumanList, '/humans/tracked', 10)

        self.get_logger().info('HumanTrackerNode 起動完了（カルマンフィルタ追跡）')

    def callback(self, msg: HumanClusterList):
        # dt を計算
        now_stamp = msg.header.stamp
        dt = 0.1  # デフォルト
        if self._last_stamp is not None:
            sec = now_stamp.sec - self._last_stamp.sec
            nanosec = now_stamp.nanosec - self._last_stamp.nanosec
            dt = max(sec + nanosec * 1e-9, 1e-3)
        self._last_stamp = now_stamp

        # F の dt を更新
        for entry in self._tracked:
            entry.kf.F[0, 2] = dt
            entry.kf.F[1, 3] = dt

        # ──────────────────────────────────────
        # 予測ステップ
        # ──────────────────────────────────────
        for entry in self._tracked:
            entry.kf.predict()

        # ──────────────────────────────────────
        # 観測との対応付け（最近傍マッチング）
        # ──────────────────────────────────────
        observations = [
            np.array([pt.x, pt.y]) for pt in msg.clusters
        ]
        matched_obs = set()

        for entry in self._tracked:
            if not entry.kf.is_initialized:
                continue
            pred_pos = np.array([entry.kf.x[0], entry.kf.x[1]])
            best_idx = -1
            best_dist = self._assoc_threshold

            for i, obs in enumerate(observations):
                if i in matched_obs:
                    continue
                d = np.linalg.norm(obs - pred_pos)
                if d < best_dist:
                    best_dist = d
                    best_idx = i

            if best_idx >= 0:
                entry.kf.update(observations[best_idx])
                entry.miss_count = 0
                matched_obs.add(best_idx)
            else:
                entry.miss_count += 1

        # ──────────────────────────────────────
        # 新規観測 → 新しいトラックを生成
        # ──────────────────────────────────────
        for i, obs in enumerate(observations):
            if i not in matched_obs:
                new_entry = TrackedEntry(self._next_id, obs, dt=dt)
                self._next_id += 1
                self._tracked.append(new_entry)

        # ──────────────────────────────────────
        # 見失いが多いトラックを削除
        # ──────────────────────────────────────
        self._tracked = [e for e in self._tracked if e.miss_count <= self._max_miss]

        # ──────────────────────────────────────
        # TrackedHumanList を発行
        # ──────────────────────────────────────
        output = TrackedHumanList()
        output.header = msg.header

        for entry in self._tracked:
            if not entry.kf.is_initialized:
                continue
            human = TrackedHuman()
            human.id = entry.id
            human.position.x = float(entry.kf.x[0])
            human.position.y = float(entry.kf.x[1])
            human.position.z = 0.0
            vel = Vector3()
            vel.x = float(entry.kf.x[2])
            vel.y = float(entry.kf.x[3])
            vel.z = 0.0
            human.velocity = vel
            output.humans.append(human)

        self.pub.publish(output)


def main(args=None):
    rclpy.init(args=args)
    node = HumanTrackerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
