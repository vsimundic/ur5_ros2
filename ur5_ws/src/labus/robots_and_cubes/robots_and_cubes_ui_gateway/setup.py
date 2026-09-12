from setuptools import find_packages, setup


package_name = 'robots_and_cubes_ui_gateway'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=[
        'setuptools', 'fastapi==0.115.12', 'uvicorn==0.34.0', 'websockets==15.0.1',
    ],
    zip_safe=True,
    maintainer='UR5 ROS 2 maintainers',
    maintainer_email='simundicv@gmail.com',
    description='Allowlisted FastAPI browser gateway for Robots and Cubes.',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'ui_gateway = robots_and_cubes_ui_gateway.main:main',
        ],
    },
)
