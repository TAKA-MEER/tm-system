from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(package='human_detection_package', executable='human_detector',
             name='human_detector', output='screen'),
        Node(package='human_detection_package', executable='human_tracker',
             name='human_tracker', output='screen'),
        Node(package='human_detection_package', executable='human_selector',
             name='human_selector', output='screen'),
        Node(package='tm_system_bringup', executable='target_point_selector',
             name='target_point_selector', output='screen'),
        Node(package='motion_control_package', executable='move_controller',
             name='move_controller', output='screen'),
        Node(package='tm_system_bringup', executable='direct_ctrl_selector',
             name='direct_ctrl_selector', output='screen'),
        Node(package='tm_system_bringup', executable='esp32_bridge',
             name='esp32_bridge', output='screen'),
    ])
