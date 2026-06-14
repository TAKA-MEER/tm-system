import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32MultiArray


class Esp32BridgeNode(Node):

    def __init__(self):
        super().__init__('esp32_bridge')
        self.sub = self.create_subscription(
            Float32MultiArray, '/crawler/cmd', self.callback, 10)

    def callback(self, msg):
        if len(msg.data) >= 2:
            self.get_logger().info(
                f'左右クローラ速度: left={msg.data[0]:.3f}, right={msg.data[1]:.3f}')


def main(args=None):
    rclpy.init(args=args)
    node = Esp32BridgeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
