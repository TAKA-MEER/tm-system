FROM ros:humble-ros-base

# 依存パッケージ
RUN apt-get update && apt-get install -y \
    python3-colcon-common-extensions \
    python3-rosdep \
    python3-pip \
    curl \
    ros-humble-rviz2 \
    ros-humble-rqt \
    ros-humble-gazebo-ros-pkgs \
    && rm -rf /var/lib/apt/lists/*

# scikit-learn のインストール
RUN pip3 install scikit-learn

# Node.js 18 のインストール（mermaid-cli 用）
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# ros2-graph と mermaid-cli のインストール
RUN pip3 install ros2-graph \
    && npm install -g @mermaid-js/mermaid-cli \
    && sed -i 's|npx -p @mermaid-js/mermaid-cli mmdc|mmdc -p /home/ros/.puppeteerrc.json|g' \
        /usr/local/lib/python3.10/dist-packages/ros2_graph/__main__.py

# Chrome のインストール（puppeteer/mermaid-cli 用）
ENV PUPPETEER_CACHE_DIR=/opt/puppeteer_cache
RUN npx -p puppeteer puppeteer browsers install chrome \
    && chmod -R a+rX /opt/puppeteer_cache \
    && rm -rf /tmp/*

# rosdepの初期化
RUN rosdep update

# 作業ユーザー（rootを避ける）
ARG USERNAME=ros
ARG USER_UID=1000
RUN useradd -m -u $USER_UID -s /bin/bash $USERNAME \
    && echo "$USERNAME ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

USER $USERNAME
WORKDIR /ros_ws

# Puppeteer設定（mermaid-cli がコンテナ内でChromeを起動できるようにする）
COPY docker/puppeteer-config.json /home/ros/.puppeteerrc.json
ENV PUPPETEER_CONFIG=/home/ros/.puppeteerrc.json

# ROS環境を自動source
RUN echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc \
    && echo "source /ros_ws/install/setup.bash 2>/dev/null || true" >> ~/.bashrc

# エントリポイント（起動時にボリュームの所有者を修正）
COPY docker/entrypoint.sh /entrypoint.sh
RUN sudo chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
CMD ["/bin/bash"]
