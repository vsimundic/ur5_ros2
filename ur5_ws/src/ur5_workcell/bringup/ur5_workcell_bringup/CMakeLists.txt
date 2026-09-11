cmake_minimum_required(VERSION 3.8)
project(ur5_workcell_bringup)

find_package(ament_cmake REQUIRED)

install(DIRECTORY config launch
  DESTINATION share/${PROJECT_NAME}
  PATTERN "__pycache__" EXCLUDE
)

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  ament_add_pytest_test(test_hardware_launch test/test_hardware_launch.py
    TIMEOUT 60
  )
endif()

ament_package()
