import math
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan


class DummyLidarPublisher(Node):

    def __init__(self):
        super().__init__('dummy_lidar_publisher')
        self.pub = self.create_publisher(LaserScan, '/scan', 10)
        self.timer = self.create_timer(0.5, self.publish_dummy)

    def publish_dummy(self):
        msg = LaserScan()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'lidar'
        msg.angle_min = -math.pi / 2
        msg.angle_max = math.pi / 2
        msg.angle_increment = math.pi / 180
        msg.time_increment = 0.0
        msg.scan_time = 0.5
        msg.range_min = 0.1
        msg.range_max = 10.0
        num_readings = 180
        msg.ranges = [float('inf')] * num_readings
        msg.intensities = [0.0] * num_readings
        center_idx = num_readings // 2
        for offset in range(-3, 4):
            idx = center_idx + offset
            if 0 <= idx < num_readings:
                msg.ranges[idx] = 2.0
        self.pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = DummyLidarPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
