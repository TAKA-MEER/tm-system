import pytest
import rclpy
from geometry_msgs.msg import PoseStamped, Twist


class TestMoveControllerDummy:

    @pytest.fixture(autouse=True)
    def setup(self):
        rclpy.init()

    def teardown_method(self):
        rclpy.shutdown()

    def test_node_construction(self):
        from motion_control_package.move_controller_node import MoveControllerNode
        node = MoveControllerNode()
        assert node is not None
        assert node.sub is not None
        assert node.pub is not None
        node.destroy_node()

    def test_pub_sub_types(self):
        from motion_control_package.move_controller_node import MoveControllerNode
        node = MoveControllerNode()
        assert node.sub.topic_name == '/target_point/selected'
        assert node.sub.msg_type == PoseStamped
        assert node.pub.topic_name == '/cmd_vel'
        assert node.pub.msg_type == Twist
        node.destroy_node()
