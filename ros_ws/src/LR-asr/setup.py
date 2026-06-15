from setuptools import find_packages, setup
import os
from glob import glob

package_name = "factory_asr"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (os.path.join("share", package_name, "launch"), glob("launch/*.py")),
        (os.path.join("share", package_name, "config"), glob("config/*.yaml")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Factory ASR Team",
    maintainer_email="dev@example.com",
    description="CPU-optimized factory speech recognition (ROS2 Humble)",
    license="Apache-2.0",
    # ★ tests_require を削除 → 新setuptools で非サポートのため警告/エラーになる
    entry_points={
        "console_scripts": [
            "audio_capture_node   = factory_asr.audio_capture_node:main",
            "preprocessor_node    = factory_asr.preprocessor_node:main",
            "asr_engine_node      = factory_asr.asr_engine_node:main",
            "output_handler_node  = factory_asr.output_handler_node:main",
        ],
    },
)
