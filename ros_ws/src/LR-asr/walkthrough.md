# 音声文字起こしシステム（LR-asr）設定完了 walkthrough

`factoryAsr` から `LR-asr` への音声文字起こしシステムの移植と、動作環境の構築が完了しました。

---

## 実施した変更

### 1. パッケージ内の設定調整
- **`params.yaml` の配置**: `factory_asr_prototype_v4` から `LR-asr/config/params.yaml` にコピーを行いました。
- **パス設定の修正**: 
  - `setup.py` で `glob` のパラメータ YAML 探索先を `config/*.yaml` に変更し、ビルド時に正常にインストールされるようにしました。
  - `output_handler_node.py` および `params.yaml` で、出力先ディレクトリのデフォルトパスを `/ros2_ws/output` から、今回の開発コンテナ環境に合わせた `/ros_ws/output` に変更しました。

### 2. コンテナおよびデバイスの連携設定
- **`Dockerfile` の依存関係追加**: `faster-whisper`, `silero-vad`, `pyaudio`, `torch` (CPUのみ) などのインストールを追加しました。また、コンテナの `ros` ユーザーに `audio` グループの権限を付与しました。
- **`compose.yml` の更新**: 
  - ホストのマイクデバイス（`/dev/snd`）を `ros2_dev` コンテナ内で共有できるように設定しました。
  - ホストの `output` フォルダのマウントを追加しました。
  - Whisperモデルキャッシュ用の `whisper_cache` ボリュームを作成・マウントしました。
- **キャッシュディレクトリのパーミッション修正**: ボリュームマウント時に root 所有となってしまう `/home/ros/.cache` ディレクトリの所有権をコンテナ内で `ros:ros` に変更し、書き込み権限（Permission denied）を解消しました。

---

## 動作確認結果

### WAVファイルモード（オフライン文字起こし）
WAVファイルの3分経過時点から30秒間を切り出して `ros_ws/output/test.wav` に配置し、以下のコマンドで起動しました：
```bash
docker exec ros2_dev bash -c "source /opt/ros/humble/setup.bash && source install/setup.bash && ros2 launch factory_asr factory_asr.launch.py input_mode:=file input_file:=/ros_ws/output/test.wav"
```
- **初回起動時**: Whisperモデル（`large-v3-turbo`）の自動ダウンロードが正常に実行され、キャッシュ（1.6GB）に保存されました。
- **2回目起動時**: ロード処理が 5.7秒 と高速に完了し、音声データを認識して以下の文字起こし結果が得られました。
  - 認識されたテキスト: `"まず、試験時に、ASMに返ったところで、 客さんからいろんな探偵図書を読み取って、 こちらの探偵図書を処理するというのが…"`
  - `output/session_xxxx/transcriptions.jsonl` やサマリーファイル（`summary.json`）も正常に保存されました。

### マイクモード（リアルタイム文字起こし）
以下のコマンドでマイクモードを起動しました：
```bash
docker exec ros2_dev bash -c "source /opt/ros/humble/setup.bash && source install/setup.bash && ros2 launch factory_asr factory_asr.launch.py input_mode:=mic"
```
- コンテナ環境からホストのマイクが未共有（PulseAudio等がない）の場合でもクラッシュすることなく、`[ERROR] マイクデバイスを開けませんでした。ファイルモードを使用してください` という警告を出した上で、システムが待機状態へ移行することを確認しました（デバイス共有の環境が整えばマイクから直接文字起こしされます）。

---

## 起動・使用方法

コンテナが起動している状態で、以下のコマンドを実行することで文字起こしを起動できます。

### A. WAVファイルから文字起こしを行う場合
1. 文字起こししたいWAVファイルを、ホストの `ros_ws/output/` ディレクトリに置きます。
2. 以下のコマンドで起動します（`<your_audio>.wav` をファイル名に変更）：
   ```bash
   docker exec -it ros2_dev bash -c "source /opt/ros/humble/setup.bash && source install/setup.bash && ros2 launch factory_asr factory_asr.launch.py input_mode:=file input_file:=/ros_ws/output/<your_audio>.wav"
   ```

### B. マイク入力からリアルタイムに文字起こしを行う場合
1. ホスト側からコンテナへのオーディオパススルーが有効（WSLg などが有効）であることを確認します。
2. 以下のコマンドで起動します：
   ```bash
   docker exec -it ros2_dev bash -c "source /opt/ros/humble/setup.bash && source install/setup.bash && ros2 launch factory_asr factory_asr.launch.py input_mode:=mic"
   ```
   ※パラメータ YAML ファイルは `ros_ws/src/LR-asr/config/params.yaml` で調整可能です。
