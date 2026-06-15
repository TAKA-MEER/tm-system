# LR-asr – 工場立ち会い試験 音声文字起こしシステム

ROS2 Humble 上の **CPU専用・高精度** 音声文字起こしプロトタイプ。  
GPU非搭載の標準的なノートPC（RAM 8 GB以上）で動作します。

**元リポジトリ**: `factory_asr_prototype_v4` → `LR-asr` へ移植・設定調整済み (詳細は [walkthrough.md](walkthrough.md))。

---

## アーキテクチャ概要

```txt
マイク入力
    │ 16kHz/Mono/16bit PCM
    ▼
┌─────────────────────────┐
│  audio_capture_node     │  マイク or WAVファイル入力
└────────┬────────────────┘
         │ /factory_asr/audio_raw (Int16MultiArray)
         ▼
┌─────────────────────────┐
│  preprocessor_node      │  Silero-VAD で無音除去
│  (+ DeepFilterNet3)     │  (オプション: ノイズ除去)
└────────┬────────────────┘
         │ /factory_asr/speech_segment (Int16MultiArray)
         ▼
┌─────────────────────────────────────────┐
│  asr_engine_node                        │
│  faster-whisper large-v3-turbo          │
│  device="cpu"  compute_type="int8"      │
│  initial_prompt: 工場専門用語           │
└────────┬────────────────────────────────┘
         │ /factory_asr/asr_result (String/JSON)
         ▼
┌─────────────────────────┐
│  output_handler_node    │  JSONL / summary.json 出力
└─────────────────────────┘
```

**期待速度**: RTF ≈ 0.3〜0.5（実時間の2〜3倍速）
（Core i5/i7 4コア、RAM 8 GB環境での目安）

---

## 前提条件

| 項目 | 要件 |
| --- | --- |
| OS | Ubuntu 22.04 LTS (Docker環境) / Windows (WSL2 Ubuntu 22.04) |
| RAM | 8 GB 以上（推奨 16 GB） |
| CPU | 4コア以上（Intel/AMD どちらも可） |
| Docker | Engine 24.0 以上 |
| GPU | **不要**（CPU専用実装） |

---

## セットアップ手順（開発コンテナ環境）

このパッケージは `ros2_dev` コンテナ内で動作します。  
tm-system トップレベルの `compose.yml` でコンテナが起動済みであることを確認してください。

```bash
# コンテナ内でパッケージビルド
docker exec ros2_dev bash -c "cd /ros_ws && colcon build --packages-select factory_asr"
```

---

## 実行方法

コンテナが起動している状態で、以下のコマンドを実行します。

### A. WAVファイルから文字起こし

1. 文字起こししたいWAVファイルをホストの `ros_ws/output/` に配置（16kHz/Mono推奨）
2. 実行:

   ```bash
   docker exec -it ros2_dev bash -c "source /opt/ros/humble/setup.bash && source install/setup.bash && ros2 launch factory_asr factory_asr.launch.py input_mode:=file input_file:=/ros_ws/output/<your_audio>.wav"
   ```

変換が必要な場合:

```bash
ffmpeg -i input.wav -ar 16000 -ac 1 ros_ws/output/test.wav
```

### B. マイクからリアルタイム文字起こし

```bash
docker exec -it ros2_dev bash -c "source /opt/ros/humble/setup.bash && source install/setup.bash && ros2 launch factory_asr factory_asr.launch.py input_mode:=mic"
```

※ パラメータ調整は `ros_ws/src/LR-asr/config/params.yaml` を編集。

---

## 出力確認

### リアルタイムでトピック監視

```bash
# ASR結果 JSON の監視
docker exec ros2_dev bash -c "source /opt/ros/humble/setup.bash && source install/setup.bash && ros2 topic echo /factory_asr/asr_result"

# 音声セグメントの統計確認
docker exec ros2_dev bash -c "source /opt/ros/humble/setup.bash && source install/setup.bash && ros2 topic hz /factory_asr/speech_segment"
```

### 出力ファイル構成

```txt
ros_ws/output/
└── session_YYYYMMDD_HHMMSS/
    ├── transcriptions.jsonl   ← 全発話（1行1JSON）
    ├── latest.json            ← 最新の発話（整形済み）
    └── summary.json           ← セッションサマリー
```

### JSON出力例

```json
{
  "utterance_id": 1,
  "timestamp_ros": 1234567890000000,
  "language": "ja",
  "language_prob": 0.9987,
  "duration_s": 4.32,
  "inference_time_s": 1.54,
  "real_time_factor": 0.357,
  "model": "large-v3-turbo",
  "device": "cpu",
  "compute_type": "int8",
  "full_text": "バルブV-201の耐圧試験、圧力1.5MPa、異常なし。",
  "segments": [
    {
      "start": 0.0,
      "end": 4.32,
      "text": "バルブV-201の耐圧試験、圧力1.5MPa、異常なし。",
      "avg_log_prob": -0.23,
      "no_speech_prob": 0.01,
      "words": [
        {"word": "バルブ", "start": 0.12, "end": 0.56, "probability": 0.98}
      ]
    }
  ]
}
```

---

## パラメータ調整

### initial_prompt のカスタマイズ（認識精度向上）

`config/params.yaml` の `initial_prompt` に現場固有の用語を追加:

```yaml
asr_engine:
  ros__parameters:
    initial_prompt: >
      工場立ち会い試験。製品検査、品質管理、
      # ← ここにプラント固有の機器名・規格番号・略語を追加
      ポンプP-101、熱交換器E-201、タービンT-301、
      JISB2220、ASME B16.5、JPI-7S-15。
```

### CPUスレッド数の調整

`config/params.yaml` の `asr_engine` セクションを編集:

```yaml
asr_engine:
  ros__parameters:
    cpu_threads: 4    # OpenBLAS/oneDNN スレッド数（コア数に合わせる）
    num_workers: 2    # CTranslate2 並列デコードワーカー
```

### ノイズ除去の有効化

```bash
# リアルタイムパラメータ変更（ノード起動中に実行）
docker exec ros2_dev bash -c "source /opt/ros/humble/setup.bash && source install/setup.bash && ros2 param set /preprocessor enable_denoiser true"
```

⚠ DeepFilterNet3 は CPU負荷を約30%増加させます。

---

## パフォーマンス目安（ノートPC）

| CPU | RAM | RTF | 備考 |
| --- | --- | --- | --- |
| Core i5-8世代 4コア | 8 GB | 0.45〜0.60 | 実用レベル |
| Core i7-10世代 6コア | 16 GB | 0.25〜0.35 | 快適 |
| Core i7-12世代 8コア | 16 GB | 0.18〜0.28 | 高速 |
| Ryzen 5 5600U | 16 GB | 0.22〜0.32 | 高速 |

RTF < 1.0 = リアルタイム以上の処理速度（上記は目安、実際の負荷状況により変動）

---

## トラブルシューティング

### マイクが認識されない

```bash
# ホスト側でデバイス確認
aplay -l
# → デバイス番号を確認して params.yaml の device_index に設定
```

WSL2環境ではホスト側PulseAudioブリッジが必要です。  
ファイルモードでの使用を推奨します。

### メモリ不足（OOM）

Docker Desktop の設定でコンテナに割り当てるメモリを増やすか、  
WSL2 の `.wslconfig` で `memory=8GB` を設定してください。

### モデルダウンロードが遅い

Whisperモデル（約1.6GB）は `whisper_cache` ボリュームにキャッシュされます。  
初回のみダウンロードが発生します（2回目以降は 約5〜6秒でロード完了）。

### ビルドエラー

```bash
docker exec ros2_dev bash -c "cd /ros_ws && colcon build --packages-select factory_asr --cmake-clean-cache"
```

---

## ライセンス

Apache-2.0

---

## 参考リンク

- [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
- [Silero-VAD](https://github.com/snakers4/silero-vad)
- [DeepFilterNet](https://github.com/Rikorose/DeepFilterNet)
- [ROS2 Humble Docs](https://docs.ros.org/en/humble/)
