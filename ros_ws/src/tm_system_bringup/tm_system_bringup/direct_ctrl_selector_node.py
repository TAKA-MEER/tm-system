import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Float32MultiArray


class DirectCtrlSelectorNode(Node):

    def __init__(self):
        super().__init__('direct_ctrl_selector')
        self.sub_auto = self.create_subscription(
            Twist, '/cmd_vel', self.callback_auto, 10)
        self.sub_manual = self.create_subscription(
            Twist, '/cmd_vel/manual', self.callback_manual, 10)
        self.pub = self.create_publisher(
            Float32MultiArray, '/crawler/cmd', 10)
        self.use_manual = False

    def callback_auto(self, msg):
        if not self.use_manual:
            self._publish_crawler_cmd(msg)

    def callback_manual(self, msg):
        if self.use_manual:
            self._publish_crawler_cmd(msg)

    def _publish_crawler_cmd(self, twist):
        output = Float32MultiArray()
        output.data = [float(twist.linear.x), float(twist.angular.z)]
        self.pub.publish(output)


def main(args=None):
    rclpy.init(args=args)
    node = DirectCtrlSelectorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
