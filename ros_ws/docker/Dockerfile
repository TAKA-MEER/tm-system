FROM ros:humble-ros-base

ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    TZ=Asia/Tokyo \
    DEBIAN_FRONTEND=noninteractive \
    CUDA_VISIBLE_DEVICES="" \
    OPENBLAS_NUM_THREADS=4 \
    OMP_NUM_THREADS=4 \
    TORCH_DEVICE="cpu"

# 依存パッケージ
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-colcon-common-extensions \
    python3-rosdep \
    python3-pip \
    curl \
    ros-humble-rviz2 \
    ros-humble-rqt \
    ros-humble-gazebo-ros-pkgs \
    python3-pip \
    python3-dev \
    python3-setuptools \
    python3-pkg-resources \
    ros-humble-rclpy \
    ros-humble-std-msgs \
    ros-humble-sensor-msgs \
    ros-humble-rmw-cyclonedds-cpp \
    libopenblas-dev \
    liblapack-dev \
    gfortran \
    ffmpeg \
    portaudio19-dev \
    pulseaudio-utils \
    libpulse0 \
    apulse \
    libsndfile1 \
    libsndfile1-dev \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

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

# pipパッケージのアップグレード
RUN pip3 install --upgrade pip
RUN pip3 install --no-cache-dir \
    "setuptools==67.8.0" \
    "wheel==0.43.0"

# PyTorch CPU-only (Python 3.10 対応)
RUN pip3 install --no-cache-dir \
    "torch==2.3.1+cpu" \
    "torchaudio==2.3.1+cpu" \
    --extra-index-url https://download.pytorch.org/whl/cpu

# faster-whisper など
RUN pip3 install --no-cache-dir \
    "faster-whisper==1.1.0" \
    "silero-vad==5.1.2" \
    "pyaudio==0.2.14" \
    "soundfile==0.12.1" \
    "numpy==1.26.4" \
    "scipy==1.13.1" \
    "pydantic==2.7.1" \
    "loguru==0.7.2"

# DeepFilterNet3 (失敗した場合は無視)
RUN pip3 install --no-cache-dir "deepfilternet==0.5.6" || \
    echo "[WARN] deepfilternet skipped."

# 作業ユーザー（rootを避ける）
ARG USERNAME=ros
ARG USER_UID=1000
RUN useradd -m -u $USER_UID -s /bin/bash -G audio $USERNAME \
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
