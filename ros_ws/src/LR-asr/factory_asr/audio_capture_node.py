#!/usr/bin/env python3
"""
audio_capture_node.py  (fixed v4)
==================================
ROS2 node: real-time microphone capture or WAV file replay

修正点:
  - マイクが見つからない場合(WSL2/Docker環境など)に
    クラッシュせずエラーログ→待機状態に移行
  - input_mode=file の場合はマイク不要
  - 利用可能なオーディオデバイス一覧をログ出力

Topic published : /factory_asr/audio_raw  (std_msgs/Int16MultiArray)
Parameters:
    sample_rate     : int   = 16000
    chunk_duration  : float = 0.5
    device_index    : int   = -1    (-1 = system default)
    input_mode      : str   = "mic" | "file"
    input_file      : str   = ""
"""

import threading
import time
import wave
from pathlib import Path
from typing import Optional

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from std_msgs.msg import Int16MultiArray, MultiArrayDimension

SAMPLE_RATE    = 16_000
CHANNELS       = 1
SAMPLE_WIDTH   = 2
FLOAT32_SCALE  = 1.0 / 32768.0


class AudioCaptureNode(Node):

    def __init__(self) -> None:
        super().__init__("audio_capture_node")

        self.declare_parameter("sample_rate",    SAMPLE_RATE)
        self.declare_parameter("chunk_duration", 0.5)
        self.declare_parameter("device_index",   -1)
        self.declare_parameter("input_mode",     "mic")
        self.declare_parameter("input_file",     "")

        self._sample_rate  = self.get_parameter("sample_rate").value
        self._chunk_dur    = self.get_parameter("chunk_duration").value
        self._device_index = self.get_parameter("device_index").value
        self._input_mode   = self.get_parameter("input_mode").value
        self._input_file   = self.get_parameter("input_file").value
        self._chunk_frames = int(self._sample_rate * self._chunk_dur)

        qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=5,
        )
        self._pub = self.create_publisher(Int16MultiArray, "/factory_asr/audio_raw", qos)

        self._running = True
        self._thread  = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

        self.get_logger().info(
            f"AudioCaptureNode ready | mode={self._input_mode} "
            f"rate={self._sample_rate} Hz chunk={self._chunk_dur:.2f}s"
        )

    # ---------------------------------------------------------------------- #
    def _capture_loop(self) -> None:
        if self._input_mode == "file":
            self._capture_from_file()
        else:
            self._capture_from_mic()

    # ---------------------------------------------------------------------- #
    def _capture_from_mic(self) -> None:
        try:
            import pyaudio
        except ImportError:
            self.get_logger().error("pyaudio not installed. Cannot use mic input.")
            return

        pa = pyaudio.PyAudio()

        # ── デバイス一覧をログ出力 (WSL2デバッグ用) ─────────────────────────
        self.get_logger().info(f"Available audio devices ({pa.get_device_count()} found):")
        for i in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(i)
            if info.get("maxInputChannels", 0) > 0:
                self.get_logger().info(
                    f"  [{i}] {info['name']}  "
                    f"(in={info['maxInputChannels']}, "
                    f"rate={int(info['defaultSampleRate'])})"
                )

        idx = self._device_index if self._device_index >= 0 else None
        stream: Optional[object] = None

        # ── 最大3回リトライ ──────────────────────────────────────────────────
        for attempt in range(3):
            try:
                stream = pa.open(
                    format=pyaudio.paInt16,
                    channels=CHANNELS,
                    rate=self._sample_rate,
                    input=True,
                    input_device_index=idx,
                    frames_per_buffer=self._chunk_frames,
                )
                self.get_logger().info("Microphone stream opened successfully.")
                break
            except OSError as e:
                self.get_logger().warn(
                    f"Mic open attempt {attempt+1}/3 failed: {e}\n"
                    "  WSL2ユーザーへ: マイクはホスト側PulseAudioブリッジが必要です。\n"
                    "  ファイル入力を推奨: docker compose --profile file up\n"
                    "  または: INPUT_FILE=/path/to/audio.wav docker compose --profile file up"
                )
                time.sleep(2.0)

        if stream is None:
            self.get_logger().error(
                "マイクデバイスを開けませんでした。\n"
                "  → ファイルモードを使用してください:\n"
                "    docker compose --profile file up\n"
                "    INPUT_FILE=/ros2_ws/output/your_audio.wav "
                "docker compose --profile file up"
            )
            pa.terminate()
            return

        try:
            while self._running and rclpy.ok():
                raw = stream.read(self._chunk_frames, exception_on_overflow=False)
                self._publish_pcm(raw)
        except Exception as exc:
            self.get_logger().error(f"Mic capture error: {exc}")
        finally:
            stream.stop_stream()
            stream.close()
            pa.terminate()

    # ---------------------------------------------------------------------- #
    def _capture_from_file(self) -> None:
        path = Path(self._input_file)
        if not path.exists():
            self.get_logger().error(
                f"Input file not found: {path}\n"
                f"  output/ フォルダに WAV ファイルを置き、\n"
                f"  INPUT_FILE=/ros2_ws/output/<file>.wav を設定してください。\n"
                f"  ffmpeg変換例: ffmpeg -i input.mp3 -ar 16000 -ac 1 output/test.wav"
            )
            return

        self.get_logger().info(f"Playing file: {path}")

        with wave.open(str(path), "rb") as wf:
            src_rate = wf.getframerate()
            src_ch   = wf.getnchannels()
            if src_rate != self._sample_rate or src_ch != 1:
                self.get_logger().warn(
                    f"WAV形式不一致: {src_rate}Hz/{src_ch}ch → 16000Hz/1ch への変換が必要\n"
                    f"  ffmpeg -i {path.name} -ar 16000 -ac 1 output/converted.wav"
                )

            total_frames = wf.getnframes()
            self.get_logger().info(
                f"Duration: {total_frames/src_rate:.1f}s  "
                f"({src_rate}Hz/{src_ch}ch/{wf.getsampwidth()*8}bit)"
            )

            while self._running and rclpy.ok():
                raw = wf.readframes(self._chunk_frames)
                if not raw:
                    self.get_logger().info("File replay complete.")
                    break
                self._publish_pcm(raw)
                time.sleep(self._chunk_dur * 0.9)

    # ---------------------------------------------------------------------- #
    def _publish_pcm(self, raw_bytes: bytes) -> None:
        samples = np.frombuffer(raw_bytes, dtype=np.int16).tolist()
        msg = Int16MultiArray()
        msg.layout.dim = [
            MultiArrayDimension(label="samples", size=len(samples), stride=len(samples))
        ]
        msg.data = samples
        self._pub.publish(msg)

    def destroy_node(self) -> None:
        self._running = False
        super().destroy_node()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = AudioCaptureNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
