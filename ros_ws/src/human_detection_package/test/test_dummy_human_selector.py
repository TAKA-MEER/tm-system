import pytest
import rclpy
from geometry_msgs.msg import PoseStamped
from tm_system_msgs.msg import TrackedHumanList


class TestHumanSelectorDummy:

    @pytest.fixture(autouse=True)
    def setup(self):
        rclpy.init()

    def teardown_method(self):
        rclpy.shutdown()

    def test_node_construction(self):
        from human_detection_package.human_selector_node import HumanSelectorNode
        node = HumanSelectorNode()
        assert node is not None
        assert node.sub is not None
        assert node.pub is not None
        node.destroy_node()

    def test_pub_sub_types(self):
        from human_detection_package.human_selector_node import HumanSelectorNode
        node = HumanSelectorNode()
        assert node.sub.topic_name == '/humans/tracked'
        assert node.sub.msg_type == TrackedHumanList
        assert node.pub.topic_name == '/humans/target_point'
        assert node.pub.msg_type == PoseStamped
        node.destroy_node()
