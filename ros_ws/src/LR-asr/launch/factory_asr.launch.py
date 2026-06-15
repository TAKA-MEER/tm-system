"""
factory_asr.launch.py
=====================
Launches all four Factory ASR nodes with shared parameter file.
"""

from pathlib import Path

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    # ── Arguments ─────────────────────────────────────────────────────────────
    params_arg = DeclareLaunchArgument(
        "params_file",
        default_value=PathJoinSubstitution(
            [FindPackageShare("factory_asr"), "config", "params.yaml"]
        ),
        description="Path to YAML parameter file",
    )

    input_mode_arg = DeclareLaunchArgument(
        "input_mode",
        default_value="mic",
        description="Audio input mode: 'mic' or 'file'",
    )

    input_file_arg = DeclareLaunchArgument(
        "input_file",
        default_value="",
        description="Path to WAV file (used when input_mode=file)",
    )

    params_file  = LaunchConfiguration("params_file")
    input_mode   = LaunchConfiguration("input_mode")
    input_file   = LaunchConfiguration("input_file")

    # ── Nodes ─────────────────────────────────────────────────────────────────
    audio_capture_node = Node(
        package="factory_asr",
        executable="audio_capture_node",
        name="audio_capture",
        output="screen",
        parameters=[
            params_file,
            {"input_mode": input_mode, "input_file": input_file},
        ],
    )

    preprocessor_node = Node(
        package="factory_asr",
        executable="preprocessor_node",
        name="preprocessor",
        output="screen",
        parameters=[params_file],
    )

    asr_engine_node = Node(
        package="factory_asr",
        executable="asr_engine_node",
        name="asr_engine",
        output="screen",
        parameters=[params_file],
    )

    output_handler_node = Node(
        package="factory_asr",
        executable="output_handler_node",
        name="output_handler",
        output="screen",
        parameters=[params_file],
    )

    return LaunchDescription(
        [
            params_arg,
            input_mode_arg,
            input_file_arg,
            LogInfo(msg="=== Factory ASR System Starting ==="),
            audio_capture_node,
            preprocessor_node,
            asr_engine_node,
            output_handler_node,
        ]
    )
