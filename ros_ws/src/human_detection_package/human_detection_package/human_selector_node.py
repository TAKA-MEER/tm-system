import numpy as np

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped

from tm_system_msgs.msg import TrackedHumanList


class HumanSelectorNode(Node):
    """
    TrackedHumanList を受け取り、追尾対象の1人を選択して
    その人物の位置を /humans/target_point (PoseStamped) として出力するノード。

    ロックオン機能：
    - 一度ターゲットを捕捉したら、カルマン予測位置に最も近い人物を優先する
    - 0.8m 以内に同一IDの人物がいればロックオン継続
    - 誰もいなければ一番近い人をターゲットにする
    """

    def __init__(self):
        super().__init__('human_selector')

        # ロックオン中のターゲットID（-1 = 未ロックオン）
        self._target_id = -1

        self.sub = self.create_subscription(
            TrackedHumanList, '/humans/tracked', self.callback, 10)
        self.pub = self.create_publisher(
            PoseStamped, '/humans/target_point', 10)

        self.get_logger().info('HumanSelectorNode 起動完了（ロックオン + ターゲット選択）')

    def callback(self, msg: TrackedHumanList):
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
