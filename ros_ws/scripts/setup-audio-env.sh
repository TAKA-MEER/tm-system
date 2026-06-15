#!/bin/bash
set -e

if grep -qi microsoft /proc/version 2>/dev/null; then
    echo "WSL2環境を検出しました"
    cp .env.wsl2.example .env
    echo ""
    echo "===================================================="
    echo "Windows側でPulseAudioサーバーを起動してください:"
    echo "  1. pulseaudio.exe を起動"
    echo "  2. default.pa に以下を追加済みであること:"
    echo "     load-module module-native-protocol-tcp auth-anonymous=1 auth-ip-acl=127.0.0.1;172.16.0.0/12"
    echo "===================================================="
else
    echo "ネイティブUbuntu環境を検出しました"
    cp .env.native.example .env

    # UIDを実際の値に置換 (PULSE_SERVER, PULSE_SOCKET_DIR 両方に適用)
    UID_VAL=$(id -u)
    sed -i "s/1000/${UID_VAL}/g" .env
fi

echo ""
echo ".env を作成しました。内容を確認してください:"
cat .env
