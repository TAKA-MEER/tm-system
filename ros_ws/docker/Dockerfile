FROM ros:humble-ros-base

# 依存パッケージ
RUN apt-get update && apt-get install -y \
    python3-colcon-common-extensions \
    python3-rosdep \
    ros-humble-rviz2 \
    ros-humble-rqt \
    ros-humble-gazebo-ros-pkgs \
    && rm -rf /var/lib/apt/lists/*

# rosdepの初期化
RUN rosdep update

# 作業ユーザー（rootを避ける）
ARG USERNAME=ros
ARG USER_UID=1000
RUN useradd -m -u $USER_UID -s /bin/bash $USERNAME \
    && echo "$USERNAME ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

USER $USERNAME
WORKDIR /ros_ws

# ROS環境を自動source
RUN echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc \
    && echo "source /ros_ws/install/setup.bash 2>/dev/null || true" >> ~/.bashrc

CMD ["/bin/bash"]
