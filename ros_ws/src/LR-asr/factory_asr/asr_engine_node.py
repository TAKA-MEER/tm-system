#!/usr/bin/env python3
"""
asr_engine_node.py
==================
ROS2 node: faster-whisper ASR (CPU-only, int8 quantisation)

Model    : large-v3-turbo
Device   : cpu   ← EXPLICITLY forced; no CUDA fallback
Compute  : int8  ← ~3× real-time speed on a 4-core laptop CPU

Subscribed topic : /factory_asr/speech_segment  (std_msgs/Int16MultiArray)
Published topic  : /factory_asr/asr_result      (std_msgs/String, JSON)

Parameters:
    model_size       : str   = "large-v3-turbo"
    language         : str   = "ja"          (ISO-639-1)
    initial_prompt   : str   = ""            (factory terminology hint)
    beam_size        : int   = 5
    vad_filter       : bool  = False         (whisper internal VAD; already done upstream)
    num_workers      : int   = 2             (CTranslate2 inter-op threads)
    cpu_threads      : int   = 4             (CTranslate2 intra-op threads)
"""

import json
import time
from typing import List, Optional, Tuple

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from std_msgs.msg import Int16MultiArray, String

# ── faster-whisper (CPU-only) ─────────────────────────────────────────────────
from faster_whisper import WhisperModel
from faster_whisper.transcribe import TranscriptionOptions

FLOAT32_SCALE = 1.0 / 32768.0
SAMPLE_RATE   = 16_000

# --------------------------------------------------------------------------- #
# Default initial_prompt for factory inspection domain
# --------------------------------------------------------------------------- #
DEFAULT_FACTORY_PROMPT = (
    "工場立ち会い試験。製品検査、品質管理、公差、トルク、圧力試験、"
    "バルブ、フランジ、ガスケット、配管、溶接、非破壊検査、超音波、"
    "放射線、磁粉、浸透探傷、引張試験、硬度、耐圧、漏洩試験。"
)


class ASREngineNode(Node):
    """Transcribes VAD-filtered speech segments using faster-whisper on CPU."""

    def __init__(self) -> None:
        super().__init__("asr_engine_node")

        # ── ROS2 parameters ───────────────────────────────────────────────────
        self.declare_parameter("model_size",     "large-v3-turbo")
        self.declare_parameter("language",       "ja")
        self.declare_parameter("initial_prompt", DEFAULT_FACTORY_PROMPT)
        self.declare_parameter("beam_size",      5)
        self.declare_parameter("vad_filter",     False)
        self.declare_parameter("num_workers",    2)
        self.declare_parameter("cpu_threads",    4)

        model_size     = self.get_parameter("model_size").value
        self._language = self.get_parameter("language").value
        self._prompt   = self.get_parameter("initial_prompt").value
        self._beam     = self.get_parameter("beam_size").value
        self._vad_filt = self.get_parameter("vad_filter").value
        num_workers    = self.get_parameter("num_workers").value
        cpu_threads    = self.get_parameter("cpu_threads").value

        # ── Load faster-whisper: device="cpu" is MANDATORY ────────────────────
        self.get_logger().info(
            f"Loading WhisperModel '{model_size}' | device=cpu | compute_type=int8 …"
        )
        t0 = time.monotonic()
        self._model = WhisperModel(
            model_size_or_path=model_size,
            device="cpu",              # ← EXPLICIT: no GPU, no CUDA
            compute_type="int8",       # ← INT8 quantisation for CPU speed
            num_workers=num_workers,   # parallel decode workers
            cpu_threads=cpu_threads,   # OpenBLAS/oneDNN thread pool
            download_root=None,        # default HuggingFace cache
        )
        elapsed = time.monotonic() - t0
        self.get_logger().info(
            f"WhisperModel loaded in {elapsed:.1f}s "
            f"(device=cpu, compute_type=int8)"
        )
        self.get_logger().info(f"initial_prompt: {self._prompt[:60]}…")

        # ── QoS ───────────────────────────────────────────────────────────────
        qos_sub = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=5,
        )
        qos_pub = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
        )

        self._sub = self.create_subscription(
            Int16MultiArray,
            "/factory_asr/speech_segment",
            self._segment_callback,
            qos_sub,
        )
        self._pub = self.create_publisher(String, "/factory_asr/asr_result", qos_pub)

        # ── Utterance counter for JSON IDs ────────────────────────────────────
        self._utterance_id = 0

        self.get_logger().info("ASREngineNode ready, waiting for speech segments.")

    # ---------------------------------------------------------------------- #
    # Callback
    # ---------------------------------------------------------------------- #
    def _segment_callback(self, msg: Int16MultiArray) -> None:
        """Receive a speech segment, run Whisper, publish JSON result."""
        # ── Decode PCM → float32 ─────────────────────────────────────────────
        pcm_int16 = np.array(msg.data, dtype=np.int16)
        audio_f32 = pcm_int16.astype(np.float32) * FLOAT32_SCALE

        segment_duration_s = len(audio_f32) / SAMPLE_RATE
        self.get_logger().info(
            f"[ASR] Received segment: {segment_duration_s:.2f}s "
            f"({len(audio_f32)} samples)"
        )

        # ── Run transcription ─────────────────────────────────────────────────
        t_start = time.monotonic()

        segments_iter, info = self._model.transcribe(
            audio=audio_f32,
            language=self._language,
            initial_prompt=self._prompt,     # ← domain terminology hint
            beam_size=self._beam,
            vad_filter=self._vad_filt,
            word_timestamps=True,            # enable word-level timing
            condition_on_previous_text=True, # contextual continuity
            # Temperature scheduling: try 0 first, fall back if logprob low
            temperature=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
            compression_ratio_threshold=2.4,
            log_prob_threshold=-1.0,
            no_speech_threshold=0.6,
        )

        # Materialise the lazy generator
        transcribed_segments: List[dict] = []
        full_text_parts: List[str] = []

        for seg in segments_iter:
            words = []
            if seg.words:
                words = [
                    {
                        "word":        w.word,
                        "start":       round(w.start, 3),
                        "end":         round(w.end, 3),
                        "probability": round(w.probability, 4),
                    }
                    for w in seg.words
                ]
            transcribed_segments.append(
                {
                    "start":              round(seg.start, 3),
                    "end":                round(seg.end, 3),
                    "text":               seg.text.strip(),
                    "avg_log_prob":       round(seg.avg_logprob, 4),
                    "no_speech_prob":     round(seg.no_speech_prob, 4),
                    "compression_ratio":  round(seg.compression_ratio, 4),
                    "words":              words,
                }
            )
            full_text_parts.append(seg.text.strip())

        t_end    = time.monotonic()
        inf_time = t_end - t_start
        rtf      = inf_time / segment_duration_s if segment_duration_s > 0 else 0.0

        self.get_logger().info(
            f"[ASR] Done: {inf_time:.2f}s inference | RTF={rtf:.2f} | "
            f"text='{' '.join(full_text_parts)[:60]}…'"
        )

        # ── Build JSON result ─────────────────────────────────────────────────
        self._utterance_id += 1
        result = {
            "utterance_id":       self._utterance_id,
            "timestamp_ros":      self.get_clock().now().nanoseconds,
            "language":           info.language,
            "language_prob":      round(info.language_probability, 4),
            "duration_s":         round(segment_duration_s, 3),
            "inference_time_s":   round(inf_time, 3),
            "real_time_factor":   round(rtf, 3),
            "model":              "large-v3-turbo",
            "device":             "cpu",
            "compute_type":       "int8",
            "full_text":          " ".join(full_text_parts),
            "segments":           transcribed_segments,
        }

        out_msg = String()
        out_msg.data = json.dumps(result, ensure_ascii=False)
        self._pub.publish(out_msg)


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def main(args=None) -> None:
    rclpy.init(args=args)
    node = ASREngineNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
