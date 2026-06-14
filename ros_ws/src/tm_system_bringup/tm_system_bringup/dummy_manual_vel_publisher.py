import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist


class DummyManualVelPublisher(Node):

    def __init__(self):
        super().__init__('dummy_manual_vel_publisher')
        self.pub = self.create_publisher(Twist, '/cmd_vel/manual', 10)
        self.timer = self.create_timer(1.0, self.publish_dummy)

    def publish_dummy(self):
        msg = Twist()
        msg.linear.x = 0.5
        msg.angular.z = 0.1
        self.pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = DummyManualVelPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
