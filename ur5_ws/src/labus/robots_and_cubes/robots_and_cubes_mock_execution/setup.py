from setuptools import find_packages, setup


package_name = 'robots_and_cubes_mock_execution'

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
    description='Hardware-free application mock for ExecutePickPlace.',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'mock_execute_pick_place = robots_and_cubes_mock_execution.action_server:main',
            'mock_game_manager = robots_and_cubes_mock_execution.mock_game_manager:main',
            'mock_backend_smoke_test = robots_and_cubes_mock_execution.smoke_test:main',
        ],
    },
)
