#!/usr/bin/env python3
"""
output_handler_node.py
======================
ROS2 node: persistent JSON transcription output

  - Subscribes to ASR results (JSON strings)
  - Appends each result to a timestamped JSONL file (one JSON per line)
  - Writes a pretty-printed "latest.json" for human review
  - Logs a coloured summary to console

Subscribed topic : /factory_asr/asr_result  (std_msgs/String, JSON)

Parameters:
    output_dir        : str  = "/ros_ws/output"
    session_name      : str  = ""     (empty = auto timestamp)
    pretty_print      : bool = True
    min_confidence    : float = 0.0   (filter segments below avg_log_prob threshold)
    log_to_console    : bool = True
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from std_msgs.msg import String


# ANSI colour codes for console readability
_CYAN  = "\033[96m"
_GREEN = "\033[92m"
_WARN  = "\033[93m"
_RESET = "\033[0m"


class OutputHandlerNode(Node):
    """Receives ASR JSON results and persists them to disk."""

    def __init__(self) -> None:
        super().__init__("output_handler_node")

        # ── Parameters ───────────────────────────────────────────────────────
        self.declare_parameter("output_dir",     "/ros_ws/output")
        self.declare_parameter("session_name",   "")
        self.declare_parameter("pretty_print",   True)
        self.declare_parameter("min_confidence", -1.5)   # avg_log_prob lower bound
        self.declare_parameter("log_to_console", True)

        self._output_dir    = Path(self.get_parameter("output_dir").value)
        session_name        = self.get_parameter("session_name").value
        self._pretty        = self.get_parameter("pretty_print").value
        self._min_conf      = self.get_parameter("min_confidence").value
        self._log_console   = self.get_parameter("log_to_console").value

        # ── Session setup ─────────────────────────────────────────────────────
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._session_id  = session_name if session_name else f"session_{ts}"
        self._session_dir = self._output_dir / self._session_id
        self._session_dir.mkdir(parents=True, exist_ok=True)

        # File paths
        self._jsonl_path  = self._session_dir / "transcriptions.jsonl"
        self._latest_path = self._session_dir / "latest.json"
        self._summary_path= self._session_dir / "summary.json"

        # In-memory accumulator for summary
        self._results       = []
        self._total_audio_s = 0.0
        self._total_inf_s   = 0.0

        # ── QoS ───────────────────────────────────────────────────────────────
        qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
        )
        self._sub = self.create_subscription(
            String, "/factory_asr/asr_result", self._result_callback, qos
        )

        # Periodic summary flush (every 60 s)
        self._summary_timer = self.create_timer(60.0, self._flush_summary)

        self.get_logger().info(
            f"OutputHandlerNode ready\n"
            f"  Session : {self._session_id}\n"
            f"  Dir     : {self._session_dir}\n"
            f"  JSONL   : {self._jsonl_path}"
        )

    # ---------------------------------------------------------------------- #
    # Result callback
    # ---------------------------------------------------------------------- #
    def _result_callback(self, msg: String) -> None:
        try:
            data = json.loads(msg.data)
        except json.JSONDecodeError as exc:
            self.get_logger().error(f"JSON parse error: {exc}")
            return

        # ── Optional confidence filter ────────────────────────────────────────
        segs = data.get("segments", [])
        filtered_segs = [
            s for s in segs
            if s.get("avg_log_prob", 0.0) >= self._min_conf
            and s.get("no_speech_prob", 1.0) < 0.8
        ]
        if len(filtered_segs) < len(segs):
            dropped = len(segs) - len(filtered_segs)
            self.get_logger().warn(
                f"[Filter] Dropped {dropped} low-confidence segment(s)."
            )
            data["segments"]  = filtered_segs
            data["full_text"] = " ".join(s["text"] for s in filtered_segs)

        # ── Append to JSONL (one result per line) ─────────────────────────────
        with open(self._jsonl_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")

        # ── Overwrite latest.json ─────────────────────────────────────────────
        indent = 2 if self._pretty else None
        with open(self._latest_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)

        # ── Update accumulators ───────────────────────────────────────────────
        self._results.append(data)
        self._total_audio_s += data.get("duration_s",       0.0)
        self._total_inf_s   += data.get("inference_time_s", 0.0)

        # ── Console log ───────────────────────────────────────────────────────
        if self._log_console:
            uid  = data.get("utterance_id",    "?")
            text = data.get("full_text",        "")
            dur  = data.get("duration_s",       0.0)
            rtf  = data.get("real_time_factor", 0.0)
            lang = data.get("language",         "?")

            rtf_colour = _GREEN if rtf < 1.0 else _WARN
            print(
                f"\n{_CYAN}━━ Utterance #{uid:04d} ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{_RESET}\n"
                f"  {_GREEN}TEXT:{_RESET} {text}\n"
                f"  Lang={lang}  Audio={dur:.2f}s  "
                f"RTF={rtf_colour}{rtf:.2f}{_RESET}  "
                f"(device=cpu, int8)\n"
            )

        self.get_logger().info(
            f"Result #{data.get('utterance_id')} saved | "
            f"text='{data.get('full_text','')[:50]}…'"
        )

    # ---------------------------------------------------------------------- #
    # Summary flush (periodic + on shutdown)
    # ---------------------------------------------------------------------- #
    def _flush_summary(self) -> None:
        if not self._results:
            return

        cumulative_rtf = (
            self._total_inf_s / self._total_audio_s
            if self._total_audio_s > 0 else 0.0
        )
        summary = {
            "session_id":       self._session_id,
            "generated_at":     datetime.now().isoformat(),
            "total_utterances": len(self._results),
            "total_audio_s":    round(self._total_audio_s, 2),
            "total_inf_s":      round(self._total_inf_s, 2),
            "cumulative_rtf":   round(cumulative_rtf, 3),
            "model":            "large-v3-turbo",
            "device":           "cpu",
            "compute_type":     "int8",
            "full_transcript":  "\n".join(
                r.get("full_text", "") for r in self._results
            ),
        }
        with open(self._summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        self.get_logger().info(
            f"Summary written → {self._summary_path} | "
            f"RTF={cumulative_rtf:.3f}"
        )

    def destroy_node(self) -> None:
        self._flush_summary()
        super().destroy_node()


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def main(args=None) -> None:
    rclpy.init(args=args)
    node = OutputHandlerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
