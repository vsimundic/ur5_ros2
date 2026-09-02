# GPU-enabled ROS 2 development image for the UR5 workcell.
# The host must provide a compatible NVIDIA driver and NVIDIA Container Toolkit.
FROM nvidia/cuda:12.8.0-cudnn-devel-ubuntu24.04

ARG ROS_DISTRO=jazzy
ARG PROJECT_NAME=ur5_ros2

LABEL org.opencontainers.image.title="${PROJECT_NAME}" \
      org.opencontainers.image.description="GPU-enabled ROS 2 Jazzy environment for the UR5 workcell"

ENV DEBIAN_FRONTEND=noninteractive \
    PROJECT_NAME=${PROJECT_NAME} \
    ROS_DISTRO=${ROS_DISTRO} \
    LANG=en_US.UTF-8 \
    LC_ALL=en_US.UTF-8

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

# Development, hardware diagnostics, ROS 2, UR, MoveIt, Gazebo and RealSense.
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
    ros-${ROS_DISTRO}-realsense2-camera \
    ros-${ROS_DISTRO}-realsense2-description \
    ros-${ROS_DISTRO}-rmw-cyclonedds-cpp \
    ros-${ROS_DISTRO}-ros-gz \
    ros-${ROS_DISTRO}-ur \
    ros-${ROS_DISTRO}-ur-simulation-gz && \
    if [ ! -e /etc/ros/rosdep/sources.list.d/20-default.list ]; then rosdep init; fi && \
    rosdep update && \
    rm -rf /var/lib/apt/lists/*

# UR does not require a specific DDS vendor. Fast DDS remains the Jazzy default;
# CycloneDDS is also installed and can be selected at runtime.
ENV ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET

# Source ROS and, when it has been built, the mounted workspace overlay.
RUN echo "source /opt/ros/${ROS_DISTRO}/setup.bash" >> /root/.bashrc && \
    echo "if [ -f /workspaces/${PROJECT_NAME}/ur5_ws/install/setup.bash ]; then source /workspaces/${PROJECT_NAME}/ur5_ws/install/setup.bash; fi" \
      >> /root/.bashrc

WORKDIR /workspaces/${PROJECT_NAME}
