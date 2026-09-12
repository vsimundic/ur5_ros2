from setuptools import find_packages, setup

setup(
    name='robots_and_cubes_calibration', version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/robots_and_cubes_calibration']),
        ('share/robots_and_cubes_calibration', ['package.xml']),
    ],
    install_requires=['setuptools'], zip_safe=True,
    maintainer='UR5 ROS 2 maintainers', maintainer_email='simundicv@gmail.com',
    description='Hardware-safe grid calibration and teaching.', license='Apache-2.0',
    tests_require=['pytest'],
)
