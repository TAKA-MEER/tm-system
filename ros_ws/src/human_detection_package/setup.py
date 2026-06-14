from setuptools import find_packages, setup

package_name = 'human_detection_package'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
         ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch',
         ['launch/human_detection_package.launch.py']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='developer',
    maintainer_email='dev@example.com',
    description='人間検知パッケージ',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'human_detector = human_detection_package.human_detector_node:main',
            'human_tracker = human_detection_package.human_tracker_node:main',
            'human_selector = human_detection_package.human_selector_node:main',
        ],
    },
)
