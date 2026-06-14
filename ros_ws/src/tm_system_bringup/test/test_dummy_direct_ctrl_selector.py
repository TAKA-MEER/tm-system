import pytest
import rclpy
from geometry_msgs.msg import Twist
from std_msgs.msg import Float32MultiArray


class TestDirectCtrlSelectorDummy:

    @pytest.fixture(autouse=True)
    def setup(self):
        rclpy.init()

    def teardown_method(self):
        rclpy.shutdown()

    def test_node_construction(self):
        from tm_system_bringup.direct_ctrl_selector_node import DirectCtrlSelectorNode
        node = DirectCtrlSelectorNode()
        assert node is not None
        node.destroy_node()

    def test_pub_sub_types(self):
        from tm_system_bringup.direct_ctrl_selector_node import DirectCtrlSelectorNode
        node = DirectCtrlSelectorNode()
        assert node.sub_auto.topic_name == '/cmd_vel'
        assert node.sub_auto.msg_type == Twist
        assert node.sub_manual.topic_name == '/cmd_vel/manual'
        assert node.sub_manual.msg_type == Twist
        assert node.pub.topic_name == '/crawler/cmd'
        assert node.pub.msg_type == Float32MultiArray
        node.destroy_node()
