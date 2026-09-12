from setuptools import find_packages, setup


package_name = 'robots_and_cubes_config'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='UR5 ROS 2 maintainers',
    maintainer_email='simundicv@gmail.com',
    description='Strict configuration models for Robots and Cubes.',
    license='Apache-2.0',
    tests_require=['pytest'],
)
