import pytest
import rclpy
from tm_system_msgs.msg import HumanClusterList, TrackedHumanList


class TestHumanTrackerDummy:

    @pytest.fixture(autouse=True)
    def setup(self):
        rclpy.init()

    def teardown_method(self):
        rclpy.shutdown()

    def test_node_construction(self):
        from human_detection_package.human_tracker_node import HumanTrackerNode
        node = HumanTrackerNode()
        assert node is not None
        assert node.sub is not None
        assert node.pub is not None
        node.destroy_node()

    def test_pub_sub_types(self):
        from human_detection_package.human_tracker_node import HumanTrackerNode
        node = HumanTrackerNode()
        assert node.sub.topic_name == '/humans/detected'
        assert node.sub.msg_type == HumanClusterList
        assert node.pub.topic_name == '/humans/tracked'
        assert node.pub.msg_type == TrackedHumanList
        node.destroy_node()
