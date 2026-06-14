import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2, PointField
import struct


class DummyLidarPublisher(Node):

    def __init__(self):
        super().__init__('dummy_lidar_publisher')
        self.pub = self.create_publisher(PointCloud2, '/lidar/points', 10)
        self.timer = self.create_timer(0.5, self.publish_dummy)

    def publish_dummy(self):
        msg = PointCloud2()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'lidar'
        msg.height = 1
        msg.width = 5
        msg.fields = [
            PointField(name='x', offset=0, datatype=PointField.FLOAT32, count=1),
            PointField(name='y', offset=4, datatype=PointField.FLOAT32, count=1),
            PointField(name='z', offset=8, datatype=PointField.FLOAT32, count=1),
        ]
        msg.is_bigendian = False
        msg.point_step = 16
        msg.row_step = msg.point_step * msg.width
        msg.is_dense = True
        points = [
            (1.0, 0.0, 0.0),
            (2.0, 0.5, 0.0),
            (2.0, -0.5, 0.0),
            (3.0, 1.0, 0.0),
            (0.5, 0.3, 0.0),
        ]
        msg.data = b''.join(
            struct.pack('<fff', x, y, z) + b'\x00' * 4
            for x, y, z in points
        )
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
