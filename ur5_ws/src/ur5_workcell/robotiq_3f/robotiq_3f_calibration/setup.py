# Copyright 2026 UR5 ROS 2 maintainers

from glob import glob

from setuptools import find_packages, setup


package_name = 'robotiq_3f_calibration'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
         ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
        ('share/' + package_name + '/rviz', glob('rviz/*.rviz')),
        ('share/' + package_name + '/urdf', glob('urdf/*.xacro')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='UR5 ROS 2 maintainers',
    maintainer_email='maintainers@example.com',
    description='Interactive calibration and measurement UI for the Robotiq 3F model.',
    license='BSD-3-Clause',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'calibration_gui = robotiq_3f_calibration.calibration_gui:main',
        ],
    },
)
