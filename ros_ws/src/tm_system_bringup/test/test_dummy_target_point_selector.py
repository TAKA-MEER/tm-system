import pytest
import rclpy
from geometry_msgs.msg import PoseStamped


class TestTargetPointSelectorDummy:

    @pytest.fixture(autouse=True)
    def setup(self):
        rclpy.init()

    def teardown_method(self):
        rclpy.shutdown()

    def test_node_construction(self):
        from tm_system_bringup.target_point_selector_node import TargetPointSelectorNode
        node = TargetPointSelectorNode()
        assert node is not None
        node.destroy_node()

    def test_pub_sub_types(self):
        from tm_system_bringup.target_point_selector_node import TargetPointSelectorNode
        node = TargetPointSelectorNode()
        assert node.sub_target.topic_name == '/humans/target_point'
        assert node.sub_target.msg_type == PoseStamped
        assert node.sub_manual.topic_name == '/target_point/manual'
        assert node.sub_manual.msg_type == PoseStamped
        assert node.pub.topic_name == '/target_point/selected'
        assert node.pub.msg_type == PoseStamped
        node.destroy_node()
