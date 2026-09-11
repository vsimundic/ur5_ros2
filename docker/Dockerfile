# GPU-enabled ROS 2 development image for the UR5 workcell.
# The host must provide a compatible NVIDIA driver and NVIDIA Container Toolkit.
FROM nvidia/cuda:12.8.0-cudnn-devel-ubuntu24.04

ARG ROS_DISTRO=jazzy
ARG PROJECT_NAME=ur5_ros2
ARG LIBREALSENSE_VERSION=2.54.2
ARG REALSENSE_ROS_VERSION=4.54.1

LABEL org.opencontainers.image.title="${PROJECT_NAME}" \
      org.opencontainers.image.description="GPU-enabled ROS 2 Jazzy environment for the UR5 workcell"

ENV DEBIAN_FRONTEND=noninteractive \
    PROJECT_NAME=${PROJECT_NAME} \
    ROS_DISTRO=${ROS_DISTRO} \
    LANG=en_US.UTF-8 \
    LC_ALL=en_US.UTF-8

COPY docker/patches/librealsense-2.54.2-gcc13.patch \
    /tmp/librealsense-2.54.2-gcc13.patch
COPY docker/patches/realsense-ros-4.54.1-jazzy.patch \
    /tmp/realsense-ros-4.54.1-jazzy.patch

# Bootstrap the ROS 2 apt repository.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    gnupg2 \
    locales \
    lsb-release && \
    locale-gen en_US en_US.UTF-8 && \
    update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8 && \
    curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
      | gpg --dearmor -o /usr/share/keyrings/ros-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(lsb_release -cs) main" \
      > /etc/apt/sources.list.d/ros2.list && \
    rm -rf /var/lib/apt/lists/*

# Development, hardware diagnostics, ROS 2, UR, MoveIt, and Gazebo.
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash-completion \
    build-essential \
    ccache \
    cmake \
    ethtool \
    gdb \
    git \
    iproute2 \
    iputils-ping \
    nano \
    netcat-openbsd \
    pciutils \
    procps \
    socat \
    sudo \
    unzip \
    usbutils \
    udev \
    vim \
    wget \
    libglvnd-dev \
    libgl1 \
    libglx0 \
    libegl1 \
    libgles2 \
    libvulkan1 \
    libssl-dev \
    libudev-dev \
    libusb-1.0-0-dev \
    pkg-config \
    mesa-utils \
    vulkan-tools \
    python3-colcon-common-extensions \
    python3-numpy \
    python3-pip \
    python3-pymodbus \
    python3-rosdep \
    python3-vcstool \
    ros-${ROS_DISTRO}-control-msgs \
    ros-${ROS_DISTRO}-desktop-full \
    ros-${ROS_DISTRO}-diagnostic-updater \
    ros-${ROS_DISTRO}-moveit \
    ros-${ROS_DISTRO}-rmw-cyclonedds-cpp \
    ros-${ROS_DISTRO}-ros-gz \
    ros-${ROS_DISTRO}-ur \
    ros-${ROS_DISTRO}-ur-simulation-gz && \
    if [ ! -e /etc/ros/rosdep/sources.list.d/20-default.list ]; then rosdep init; fi && \
    rosdep update && \
    rm -rf /var/lib/apt/lists/*

# The L515 was removed from librealsense after 2.54.2. Build the last SDK
# release that still contains it, using the user-space USB backend so the
# container does not depend on a patched host kernel module.
RUN git clone --branch "v${LIBREALSENSE_VERSION}" --depth 1 \
      https://github.com/realsenseai/librealsense.git /tmp/librealsense && \
    if [ "${LIBREALSENSE_VERSION}" = "2.54.2" ]; then \
      git -C /tmp/librealsense apply \
        /tmp/librealsense-2.54.2-gcc13.patch; \
    fi && \
    cmake -S /tmp/librealsense -B /tmp/librealsense/build \
      -DCMAKE_BUILD_TYPE=Release \
      -DFORCE_RSUSB_BACKEND=ON \
      -DBUILD_EXAMPLES=OFF \
      -DBUILD_GRAPHICAL_EXAMPLES=OFF \
      -DBUILD_TOOLS=ON \
      -DBUILD_UNIT_TESTS=OFF \
      -DBUILD_WITH_CUDA=OFF && \
    cmake --build /tmp/librealsense/build --parallel "$(nproc)" && \
    cmake --install /tmp/librealsense/build && \
    ldconfig && \
    rm -rf /tmp/librealsense /tmp/librealsense-2.54.2-gcc13.patch

# Build the matching ROS 2 wrapper in an isolated, image-owned overlay. This
# prevents the Jazzy binary package from upgrading librealsense past L515
# support while leaving the mounted project workspace independent.
RUN mkdir -p /opt/realsense_ws/src && \
    git clone --branch "${REALSENSE_ROS_VERSION}" --depth 1 \
      https://github.com/realsenseai/realsense-ros.git \
      /opt/realsense_ws/src/realsense-ros && \
    if [ "${REALSENSE_ROS_VERSION}" = "4.54.1" ]; then \
      git -C /opt/realsense_ws/src/realsense-ros apply \
        /tmp/realsense-ros-4.54.1-jazzy.patch; \
    fi && \
    . "/opt/ros/${ROS_DISTRO}/setup.sh" && \
    rosdep install --from-paths /opt/realsense_ws/src --ignore-src \
      --rosdistro "${ROS_DISTRO}" --skip-keys=librealsense2 -r -y && \
    colcon --log-base /tmp/realsense_log build \
      --base-paths /opt/realsense_ws/src \
      --build-base /tmp/realsense_build \
      --install-base /opt/realsense_ws/install \
      --cmake-args -DCMAKE_BUILD_TYPE=Release && \
    test "$(pkg-config --modversion realsense2)" = \
      "${LIBREALSENSE_VERSION}" && \
    . /opt/realsense_ws/install/setup.sh && \
    test "$(ros2 pkg prefix realsense2_camera)" = \
      /opt/realsense_ws/install/realsense2_camera && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    rm -rf /tmp/realsense_build /tmp/realsense_log \
      /tmp/realsense-ros-4.54.1-jazzy.patch \
      /opt/realsense_ws/src/realsense-ros/.git

# UR does not require a specific DDS vendor. Fast DDS remains the Jazzy default;
# CycloneDDS is also installed and can be selected at runtime.
ENV ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET

# Source ROS and, when it has been built, the mounted workspace overlay.
RUN echo "source /opt/ros/${ROS_DISTRO}/setup.bash" >> /root/.bashrc && \
    echo "source /opt/realsense_ws/install/setup.bash" >> /root/.bashrc && \
    echo "if [ -f /workspaces/${PROJECT_NAME}/ur5_ws/install/local_setup.bash ]; then source /workspaces/${PROJECT_NAME}/ur5_ws/install/local_setup.bash; fi" \
      >> /root/.bashrc

WORKDIR /workspaces/${PROJECT_NAME}
