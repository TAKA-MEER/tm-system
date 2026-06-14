import pytest
import rclpy
from sensor_msgs.msg import PointCloud2
from tm_system_msgs.msg import HumanClusterList


class TestHumanDetectorDummy:

    @pytest.fixture(autouse=True)
    def setup(self):
        rclpy.init()

    def teardown_method(self):
        rclpy.shutdown()

    def test_node_construction(self):
        from human_detection_package.human_detector_node import HumanDetectorNode
        node = HumanDetectorNode()
        assert node is not None
        assert node.sub is not None
        assert node.pub is not None
        node.destroy_node()

    def test_pub_sub_types(self):
        from human_detection_package.human_detector_node import HumanDetectorNode
        node = HumanDetectorNode()
        sub_info = node.sub
        pub_info = node.pub
        assert sub_info.topic_name == '/lidar/points'
        assert sub_info.msg_type == PointCloud2
        assert pub_info.topic_name == '/humans/detected'
        assert pub_info.msg_type == HumanClusterList
        node.destroy_node()
