from setuptools import find_packages, setup

package_name = 'motion_control_package'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
         ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch',
         ['launch/motion_control_package.launch.py']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='developer',
    maintainer_email='dev@example.com',
    description='移動処理パッケージ',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'move_controller = motion_control_package.move_controller_node:main',
        ],
    },
)
