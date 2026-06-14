from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='motion_control_package',
            executable='move_controller',
            name='move_controller',
            output='screen',
        ),
    ])
