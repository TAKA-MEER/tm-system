import rclpy
from rclpy.node import Node
from tm_system_msgs.msg import HumanClusterList, TrackedHumanList


class HumanTrackerNode(Node):

    def __init__(self):
        super().__init__('human_tracker')
        self.sub = self.create_subscription(
            HumanClusterList, '/humans/detected', self.callback, 10)
        self.pub = self.create_publisher(
            TrackedHumanList, '/humans/tracked', 10)

    def callback(self, msg):
        output = TrackedHumanList()
        output.header = msg.header
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
