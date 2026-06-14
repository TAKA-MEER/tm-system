import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped


class DummyManualTargetPublisher(Node):

    def __init__(self):
        super().__init__('dummy_manual_target_publisher')
        self.pub = self.create_publisher(
            PoseStamped, '/target_point/manual', 10)
        self.timer = self.create_timer(1.0, self.publish_dummy)

    def publish_dummy(self):
        msg = PoseStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'map'
        msg.pose.position.x = 2.0
        msg.pose.position.y = 1.0
        msg.pose.position.z = 0.0
        self.pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = DummyManualTargetPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
