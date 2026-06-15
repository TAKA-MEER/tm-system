#!/usr/bin/env python3
"""
preprocessor_node.py
====================
ROS2 node: VAD-gated audio preprocessing
  - Silero-VAD (CPU, torch.jit) for voice activity detection
  - Accumulates speech frames into a segment buffer
  - Optional DeepFilterNet3 noise suppression (toggleable at runtime)
  - Publishes validated speech segments ready for ASR

Subscribed topic : /factory_asr/audio_raw      (std_msgs/Int16MultiArray)
Published topic  : /factory_asr/speech_segment (std_msgs/Int16MultiArray)

Parameters:
    vad_threshold      : float = 0.5   (0.0–1.0, higher = more strict)
    vad_min_silence_ms : int   = 300   (ms of silence before segment flush)
    vad_min_speech_ms  : int   = 100   (ms of speech before VAD fires)
    max_segment_s      : float = 30.0  (force-flush upper bound, seconds)
    enable_denoiser    : bool  = False (DeepFilterNet3 toggle)
    sample_rate        : int   = 16000
"""

from collections import deque
from typing import Deque, List, Optional

import numpy as np
import torch
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from std_msgs.msg import Int16MultiArray, MultiArrayDimension


# Silero-VAD uses 512-sample windows at 16 kHz
VAD_WINDOW_SAMPLES = 512
SAMPLE_RATE        = 16_000
FLOAT32_SCALE      = 1.0 / 32768.0   # int16 → float32 normalisation


class PreprocessorNode(Node):
    """VAD-gated audio preprocessor with optional DeepFilterNet3."""

    def __init__(self) -> None:
        super().__init__("preprocessor_node")

        # ── Parameters ───────────────────────────────────────────────────────
        self.declare_parameter("vad_threshold",       0.5)
        self.declare_parameter("vad_min_silence_ms",  300)
        self.declare_parameter("vad_min_speech_ms",   100)
        self.declare_parameter("max_segment_s",       30.0)
        self.declare_parameter("enable_denoiser",     False)
        self.declare_parameter("sample_rate",         SAMPLE_RATE)

        self._threshold      = self.get_parameter("vad_threshold").value
        self._min_silence    = self.get_parameter("vad_min_silence_ms").value
        self._min_speech     = self.get_parameter("vad_min_speech_ms").value
        self._max_segment_s  = self.get_parameter("max_segment_s").value
        self._enable_denoise = self.get_parameter("enable_denoiser").value
        self._sample_rate    = self.get_parameter("sample_rate").value

        self._max_segment_samples = int(self._max_segment_s * self._sample_rate)

        # ── Silence / speech counters (in samples) ────────────────────────────
        self._silence_samples = 0
        self._speech_samples  = 0
        self._min_silence_smp = int(self._min_silence * self._sample_rate / 1000)
        self._min_speech_smp  = int(self._min_speech  * self._sample_rate / 1000)

        # ── Segment accumulation buffer ───────────────────────────────────────
        self._segment: List[float] = []   # float32 samples

        # ── Load Silero-VAD (CPU, no CUDA) ────────────────────────────────────
        self.get_logger().info("Loading Silero-VAD model (CPU)…")
        self._vad_model, self._vad_utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            force_reload=False,
            onnx=False,    # use TorchScript JIT for CPU
        )
        self._vad_model.eval()
        # Reset per-stream hidden state
        self._vad_model.reset_states()
        self.get_logger().info("Silero-VAD loaded.")

        # ── Load DeepFilterNet3 (optional) ────────────────────────────────────
        self._df_state   = None
        self._df_model   = None
        if self._enable_denoise:
            self._load_deepfilter()
        else:
            self.get_logger().info("DeepFilterNet3 disabled (enable_denoiser=False).")

        # ── Add parameter listener for live toggle ────────────────────────────
        self.add_on_set_parameters_callback(self._on_param_change)

        # ── ROS2 pub/sub ──────────────────────────────────────────────────────
        qos_sub = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
        )
        qos_pub = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=5,
        )

        self._sub = self.create_subscription(
            Int16MultiArray,
            "/factory_asr/audio_raw",
            self._audio_callback,
            qos_sub,
        )
        self._pub = self.create_publisher(
            Int16MultiArray, "/factory_asr/speech_segment", qos_pub
        )

        self.get_logger().info(
            f"PreprocessorNode ready | VAD threshold={self._threshold} "
            f"denoise={'ON' if self._enable_denoise else 'OFF'}"
        )

    # ---------------------------------------------------------------------- #
    # Dynamic parameter update (live denoiser toggle)
    # ---------------------------------------------------------------------- #
    def _on_param_change(self, params):
        from rcl_interfaces.msg import SetParametersResult
        for p in params:
            if p.name == "enable_denoiser":
                if p.value and self._df_model is None:
                    self._load_deepfilter()
                elif not p.value:
                    self._df_model  = None
                    self._df_state  = None
                    self.get_logger().info("DeepFilterNet3 deactivated.")
                self._enable_denoise = p.value
        return SetParametersResult(successful=True)

    # ---------------------------------------------------------------------- #
    # DeepFilterNet3 loader
    # ---------------------------------------------------------------------- #
    def _load_deepfilter(self) -> None:
        try:
            from df.enhance import init_df, enhance  # deepfilternet package
            self._df_model, self._df_state, _ = init_df()
            self._df_enhance = enhance
            self.get_logger().info("DeepFilterNet3 loaded (CPU).")
        except ImportError:
            self.get_logger().warn(
                "deepfilternet not installed – skipping noise suppression. "
                "Install with: pip install deepfilternet"
            )
            self._enable_denoise = False

    # ---------------------------------------------------------------------- #
    # Audio callback
    # ---------------------------------------------------------------------- #
    def _audio_callback(self, msg: Int16MultiArray) -> None:
        # Convert int16 list → float32 numpy array
        pcm_int16  = np.array(msg.data, dtype=np.int16)
        pcm_float  = pcm_int16.astype(np.float32) * FLOAT32_SCALE

        # Optional denoising (applied before VAD for cleaner speech detection)
        if self._enable_denoise and self._df_model is not None:
            pcm_float = self._denoise(pcm_float)

        # Feed into VAD window-by-window
        offset = 0
        while offset + VAD_WINDOW_SAMPLES <= len(pcm_float):
            window = pcm_float[offset : offset + VAD_WINDOW_SAMPLES]
            self._process_vad_window(window)
            offset += VAD_WINDOW_SAMPLES

    def _process_vad_window(self, window: np.ndarray) -> None:
        """Run Silero-VAD on one 512-sample window and manage segment state."""
        tensor = torch.from_numpy(window).unsqueeze(0)  # (1, 512)

        with torch.no_grad():
            speech_prob: float = self._vad_model(tensor, self._sample_rate).item()

        is_speech = speech_prob >= self._threshold

        if is_speech:
            self._silence_samples  = 0
            self._speech_samples  += VAD_WINDOW_SAMPLES
            self._segment.extend(window.tolist())
        else:
            self._silence_samples += VAD_WINDOW_SAMPLES
            # Keep a short tail to avoid cutting off word endings
            if self._speech_samples > 0:
                self._segment.extend(window.tolist())

        # ── Flush conditions ────────────────────────────────────────────────
        should_flush = False

        # 1. Natural end of speech (min silence elapsed after min speech)
        if (
            self._speech_samples >= self._min_speech_smp
            and self._silence_samples >= self._min_silence_smp
        ):
            should_flush = True

        # 2. Hard upper limit (prevent unbounded buffer)
        if len(self._segment) >= self._max_segment_samples:
            should_flush = True
            self.get_logger().warn(
                f"Segment exceeded max length ({self._max_segment_s}s) – forcing flush."
            )

        if should_flush and self._speech_samples >= self._min_speech_smp:
            self._flush_segment()

    def _flush_segment(self) -> None:
        """Publish accumulated speech segment and reset state."""
        if not self._segment:
            return

        # Convert float32 back to int16 for transmission
        arr_f  = np.array(self._segment, dtype=np.float32)
        arr_i  = (arr_f / FLOAT32_SCALE).clip(-32768, 32767).astype(np.int16)

        msg = Int16MultiArray()
        msg.layout.dim = [
            MultiArrayDimension(
                label="samples",
                size=len(arr_i),
                stride=len(arr_i),
            )
        ]
        msg.data = arr_i.tolist()
        self._pub.publish(msg)

        dur_s = len(arr_i) / self._sample_rate
        self.get_logger().info(
            f"Speech segment published: {dur_s:.2f}s "
            f"({len(arr_i)} samples)"
        )

        # Reset accumulators
        self._segment        = []
        self._speech_samples  = 0
        self._silence_samples = 0
        # Reset VAD hidden state for next utterance
        self._vad_model.reset_states()

    # ---------------------------------------------------------------------- #
    # DeepFilterNet3 inference
    # ---------------------------------------------------------------------- #
    def _denoise(self, pcm: np.ndarray) -> np.ndarray:
        import soundfile as sf
        import io, torch

        # deepfilternet expects (channels, samples) tensor at its native sr
        audio_tensor = torch.from_numpy(pcm).unsqueeze(0)  # (1, N)
        enhanced = self._df_enhance(
            self._df_model, self._df_state, audio_tensor
        )
        return enhanced.squeeze(0).numpy()


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def main(args=None) -> None:
    rclpy.init(args=args)
    node = PreprocessorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
