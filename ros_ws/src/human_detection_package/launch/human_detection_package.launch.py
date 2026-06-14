from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='human_detection_package',
            executable='human_detector',
            name='human_detector',
            output='screen',
        ),
        Node(
            package='human_detection_package',
            executable='human_tracker',
            name='human_tracker',
            output='screen',
        ),
        Node(
            package='human_detection_package',
            executable='human_selector',
            name='human_selector',
            output='screen',
        ),
    ])
