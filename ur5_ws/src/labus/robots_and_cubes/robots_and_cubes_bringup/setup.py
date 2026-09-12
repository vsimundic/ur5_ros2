from glob import glob

from setuptools import setup


package_name = 'robots_and_cubes_bringup'

setup(
    name=package_name,
    version='0.1.0',
    packages=[],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='UR5 ROS 2 maintainers',
    maintainer_email='simundicv@gmail.com',
    description='Explicit application bringup for Robots and Cubes.',
    license='Apache-2.0',
    tests_require=['pytest'],
)
