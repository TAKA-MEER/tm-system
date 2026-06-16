from setuptools import find_packages, setup

package_name = 'tm_system_bringup'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
         ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch',
         ['launch/tm_system_all.launch.py',
          'launch/dummy_topics.launch.py']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='developer',
    maintainer_email='dev@example.com',
    description='TMシステム起動・統合',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'target_point_selector = tm_system_bringup.target_point_selector_node:main',
            'direct_ctrl_selector = tm_system_bringup.direct_ctrl_selector_node:main',
            'esp32_bridge = tm_system_bringup.esp32_bridge_node:main',
            'dummy_lidar_publisher = tm_system_bringup.dummy_lidar_publisher:main',
            'dummy_manual_target_publisher = tm_system_bringup.dummy_manual_target_publisher:main',
            'dummy_manual_vel_publisher = tm_system_bringup.dummy_manual_vel_publisher:main',
        ],
    },
)
