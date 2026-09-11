#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

IMAGE_NAME="${IMAGE_NAME:-ur5_ros2}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
CONTAINER_NAME="${CONTAINER_NAME:-ur5_ros2_dev}"
CONTAINER_WS="${CONTAINER_WS:-/workspaces/ur5_ros2}"
GPU_REQUEST="${GPU_REQUEST:-all}"
ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-0}"
RMW_IMPLEMENTATION="${RMW_IMPLEMENTATION:-rmw_fastrtps_cpp}"
ROS_AUTOMATIC_DISCOVERY_RANGE="${ROS_AUTOMATIC_DISCOVERY_RANGE:-SUBNET}"
LEGACY_PROJECT_HOST="${LEGACY_PROJECT_HOST:-/home/robot/projects/ur5-door-interaction}"
LEGACY_PROJECT_CONTAINER="${LEGACY_PROJECT_CONTAINER:-/opt/reference/ur5-door-interaction}"

if [[ ! -d "${LEGACY_PROJECT_HOST}" ]]; then
    printf 'Legacy project directory not found: %s\n' "${LEGACY_PROJECT_HOST}" >&2
    exit 1
fi

if docker container inspect "${CONTAINER_NAME}" >/dev/null 2>&1; then
    docker container rm --force "${CONTAINER_NAME}" >/dev/null
fi

docker run \
    --interactive \
    --tty \
    --network=host \
    --gpus="${GPU_REQUEST}" \
    --env="DISPLAY=${DISPLAY:-}" \
    --env=NVIDIA_DRIVER_CAPABILITIES=all \
    --env=QT_X11_NO_MITSHM=1 \
    --env=XDG_RUNTIME_DIR=/tmp/runtime-root \
    --env="ROS_DOMAIN_ID=${ROS_DOMAIN_ID}" \
    --env="RMW_IMPLEMENTATION=${RMW_IMPLEMENTATION}" \
    --env="ROS_AUTOMATIC_DISCOVERY_RANGE=${ROS_AUTOMATIC_DISCOVERY_RANGE}" \
    --shm-size=10g \
    --ulimit=rtprio=99 \
    --ulimit=memlock=-1 \
    --volume=/tmp/.X11-unix:/tmp/.X11-unix:rw \
    --volume=/dev/bus/usb:/dev/bus/usb:rw \
    --volume=/usr/share/vulkan/icd.d:/usr/share/vulkan/icd.d:ro \
    --volume="${PROJECT_ROOT}:${CONTAINER_WS}" \
    --mount="type=bind,source=${LEGACY_PROJECT_HOST},target=${LEGACY_PROJECT_CONTAINER},readonly" \
    --workdir="${CONTAINER_WS}" \
    --privileged \
    --name="${CONTAINER_NAME}" \
    "${IMAGE_NAME}:${IMAGE_TAG}"
