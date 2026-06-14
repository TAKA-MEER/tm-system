import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2
from tm_system_msgs.msg import HumanClusterList


class HumanDetectorNode(Node):

    def __init__(self):
        super().__init__('human_detector')
        self.sub = self.create_subscription(
            PointCloud2, '/lidar/points', self.callback, 10)
        self.pub = self.create_publisher(
            HumanClusterList, '/humans/detected', 10)

    def callback(self, msg):
        output = HumanClusterList()
        output.header = msg.header
        self.pub.publish(output)


def main(args=None):
    rclpy.init(args=args)
    node = HumanDetectorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
