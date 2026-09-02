#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

IMAGE_NAME="${IMAGE_NAME:-ur5_ros2}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

docker build \
    --file "${SCRIPT_DIR}/Dockerfile" \
    --tag "${IMAGE_NAME}:${IMAGE_TAG}" \
    "${PROJECT_ROOT}"

printf '\nSuccessfully built Docker image: %s:%s\n' "${IMAGE_NAME}" "${IMAGE_TAG}"
