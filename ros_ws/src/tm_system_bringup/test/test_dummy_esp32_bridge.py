import pytest
import rclpy
from std_msgs.msg import Float32MultiArray


class TestEsp32BridgeDummy:

    @pytest.fixture(autouse=True)
    def setup(self):
        rclpy.init()

    def teardown_method(self):
        rclpy.shutdown()

    def test_node_construction(self):
        from tm_system_bringup.esp32_bridge_node import Esp32BridgeNode
        node = Esp32BridgeNode()
        assert node is not None
        assert node.sub is not None
        node.destroy_node()

    def test_sub_type(self):
        from tm_system_bringup.esp32_bridge_node import Esp32BridgeNode
        node = Esp32BridgeNode()
        assert node.sub.topic_name == '/crawler/cmd'
        assert node.sub.msg_type == Float32MultiArray
        node.destroy_node()
