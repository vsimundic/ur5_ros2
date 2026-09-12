cmake_minimum_required(VERSION 3.8)
project(robots_and_cubes_interfaces)

find_package(ament_cmake REQUIRED)
find_package(builtin_interfaces REQUIRED)
find_package(rosidl_default_generators REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "action/ExecutePickPlace.action"
  "msg/CubeState.msg"
  "msg/CalibrationStatus.msg"
  "msg/ErrorSummary.msg"
  "msg/GameStateSnapshot.msg"
  "msg/TaughtPositionInfo.msg"
  "srv/AcceptGridCalibration.srv"
  "srv/AcceptTaughtPosition.srv"
  "srv/AbortRound.srv"
  "srv/CancelGridCalibration.srv"
  "srv/CaptureCalibrationPoint.srv"
  "srv/CaptureTaughtPosition.srv"
  "srv/ConfirmPhysicalSetup.srv"
  "srv/ConfigureMockOutcome.srv"
  "srv/DeleteTaughtPosition.srv"
  "srv/GenerateRound.srv"
  "srv/GetCalibrationStatus.srv"
  "srv/GetGameState.srv"
  "srv/ListTaughtPositions.srv"
  "srv/ReconcileOperation.srv"
  "srv/RetryOperation.srv"
  "srv/StartGridCalibration.srv"
  "srv/SubmitChildSelection.srv"
  "srv/ValidateGridCalibration.srv"
  DEPENDENCIES builtin_interfaces
)

ament_export_dependencies(rosidl_default_runtime)
ament_package()
