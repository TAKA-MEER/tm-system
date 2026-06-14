import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped, Twist


class MoveControllerNode(Node):

    def __init__(self):
        super().__init__('move_controller')
        self.sub = self.create_subscription(
            PoseStamped, '/target_point/selected', self.callback, 10)
        self.pub = self.create_publisher(
            Twist, '/cmd_vel', 10)

    def callback(self, msg):
        output = Twist()
        self.pub.publish(output)


def main(args=None):
    rclpy.init(args=args)
    node = MoveControllerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
