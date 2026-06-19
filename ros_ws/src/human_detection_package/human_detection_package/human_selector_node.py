import numpy as np

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import Bool

from tm_system_msgs.msg import TrackedHumanList


class HumanSelectorNode(Node):
    """
    TrackedHumanList を受け取り、追尾対象の1人を選択して
    その人物の位置を /humans/target_point (PoseStamped) として出力するノード。

    安全機能：
    - /safety/obstacle_near が True の間は target_point を発行しない
    - これにより走行系（move_controller 以降）が完全に停止する

    ロックオン機能：
    - 一度ターゲットを捕捉したら、同じ ID の人物を優先追跡する
    - 誰もいなければ一番近い人をターゲットにする
    """

    def __init__(self):
        super().__init__('human_selector')

        # ロックオン中のターゲットID（-1 = 未ロックオン）
        self._target_id = -1

        # 安全フラグ（True のとき走行系への出力を停止）
        self._obstacle_near = False

        self.sub = self.create_subscription(
            TrackedHumanList, '/humans/tracked', self.callback, 10)
        # 安全停止フラグを受け取る
        self.safety_sub = self.create_subscription(
            Bool, '/safety/obstacle_near', self.safety_callback, 10)
        self.pub = self.create_publisher(
            PoseStamped, '/humans/target_point', 10)

        self.get_logger().info('HumanSelectorNode 起動完了（安全停止 + ロックオン）')

    def safety_callback(self, msg: Bool):
        """障害物接近フラグを受け取る"""
        prev = self._obstacle_near
        self._obstacle_near = msg.data
        # 状態が変わったときだけログを出す
        if self._obstacle_near and not prev:
            self.get_logger().warn(
                '🛑 安全停止モード ON: 0.8m以内に障害物 → 走行系への出力を停止'
            )
        elif not self._obstacle_near and prev:
            self.get_logger().info(
                '✅ 安全停止モード OFF: 障害物なし → 走行系への出力を再開'
            )

    def callback(self, msg: TrackedHumanList):
        # ──────────────────────────────────────
        # 安全停止チェック: obstacle_near なら何もしない
        # ──────────────────────────────────────
        if self._obstacle_near:
            return  # target_point を発行しない → 走行系は動かない

        if not msg.humans:
            # 誰も検知されなければロックオン解除
            self._target_id = -1
            return

        target = None

        if self._target_id >= 0:
            # ──────────────────────────────────────
            # ロックオン中：同じ ID の人物を探す
            # ──────────────────────────────────────
            for human in msg.humans:
                if human.id == self._target_id:
                    target = human
                    break

            if target is None:
                # ID が消えた場合はロックオン解除して最近傍へ
                self._target_id = -1

        if target is None:
            # ──────────────────────────────────────
            # 未ロックオン or ID消失：最も近い人を選ぶ
            # ──────────────────────────────────────
            target = min(
                msg.humans,
                key=lambda h: np.linalg.norm([h.position.x, h.position.y])
            )
            self._target_id = target.id
            self.get_logger().info(
                f'ターゲットロックオン: id={self._target_id} '
                f'({target.position.x:.2f}, {target.position.y:.2f})'
            )

        # ──────────────────────────────────────
        # /humans/target_point を発行
        # ──────────────────────────────────────
        out = PoseStamped()
        out.header = msg.header
        out.pose.position.x = target.position.x
        out.pose.position.y = target.position.y
        out.pose.position.z = target.position.z
        out.pose.orientation.w = 1.0
        self.pub.publish(out)


def main(args=None):
    rclpy.init(args=args)
    node = HumanSelectorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
