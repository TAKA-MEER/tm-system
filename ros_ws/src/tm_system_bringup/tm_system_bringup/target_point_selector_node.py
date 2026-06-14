import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped


class TargetPointSelectorNode(Node):

    def __init__(self):
        super().__init__('target_point_selector')
        self.sub_target = self.create_subscription(
            PoseStamped, '/humans/target_point', self.callback_target, 10)
        self.sub_manual = self.create_subscription(
            PoseStamped, '/target_point/manual', self.callback_manual, 10)
        self.pub = self.create_publisher(
            PoseStamped, '/target_point/selected', 10)
        self.latest_target = None
        self.latest_manual = None
        self.use_manual = False

    def callback_target(self, msg):
        self.latest_target = msg
        if not self.use_manual:
            self.pub.publish(msg)

    def callback_manual(self, msg):
        self.latest_manual = msg
        if self.use_manual:
            self.pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = TargetPointSelectorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
