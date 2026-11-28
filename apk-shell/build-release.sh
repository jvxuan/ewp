#!/bin/bash
# 正式版打包：编译 + 对齐 + release 签名
# 用法：PEW_PASS=<密钥库口令> bash apk-shell/build-release.sh <版本号，如 2.71>
# 前提：.keystore/pew-release.keystore 已存在（别名 pew-release）
set -e
VER="$1"
if [ -z "$VER" ]; then echo "用法：PEW_PASS=<口令> bash apk-shell/build-release.sh 2.71"; exit 1; fi
if [ -z "$PEW_PASS" ]; then echo "缺少环境变量 PEW_PASS（release 密钥库口令）"; exit 1; fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
KS="$ROOT/.keystore/pew-release.keystore"
[ -f "$KS" ] || { echo "找不到密钥库：$KS"; exit 1; }

cp "$ROOT/notes-app/index.html" "$ROOT/apk-shell/assets/index.html"
bash "$ROOT/apk-shell/build.sh"

BT="$HOME/android-sdk/build-tools/34.0.0"
OUT="$ROOT/PEW-release-v$VER.apk"
"$BT/apksigner" sign --ks "$KS" --ks-pass pass:"$PEW_PASS" --key-pass pass:"$PEW_PASS" \
  --v1-signing-enabled true --v2-signing-enabled true \
  --out "$OUT" "$ROOT/apk-shell/build/aligned.apk"

"$BT/apksigner" verify --print-certs "$OUT" | head -3
"$BT/aapt2" dump badging "$OUT" | head -1
echo "RELEASE OK -> $OUT"
