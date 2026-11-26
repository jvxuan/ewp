#!/bin/bash
set -e
unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy ALL_PROXY all_proxy PROXY
export JAVA_HOME=/home/user/Doubao/chats/38456277170402306/.tools/jdk-11.0.33.1+1
export PATH=$JAVA_HOME/bin:$PATH
BT=$HOME/android-sdk/build-tools/34.0.0
AJAR=$HOME/android-sdk/platforms/android-34/android.jar
cd "$(dirname "$0")"
rm -rf build/gen build/classes build/dex build/res.zip build/base.apk build/unsigned.apk build/aligned.apk build/yizhizuo-debug.apk
mkdir -p build/gen build/classes build/dex

$BT/aapt2 compile --dir res -o build/res.zip
$BT/aapt2 link -I "$AJAR" --manifest AndroidManifest.xml -A assets -o build/base.apk --java build/gen build/res.zip

javac -cp "$AJAR" -d build/classes \
  src/com/yizhizuo/app/MainActivity.java build/gen/com/yizhizuo/app/R.java

$BT/d8 --lib "$AJAR" --min-api 21 --output build/dex $(find build/classes -name '*.class')

cp build/base.apk build/unsigned.apk
python3 -c "
import zipfile
with zipfile.ZipFile('build/unsigned.apk','a',zipfile.ZIP_DEFLATED) as z:
    z.write('build/dex/classes.dex','classes.dex')
"

$BT/zipalign -f 4 build/unsigned.apk build/aligned.apk
if [ ! -f build/debug.keystore ]; then
  keytool -genkeypair -v -keystore build/debug.keystore -alias androiddebugkey \
    -keyalg RSA -keysize 2048 -validity 10000 -storepass android -keypass android \
    -dname "CN=Android Debug,O=Android,C=US"
fi
$BT/apksigner sign --ks build/debug.keystore --ks-pass pass:android --key-pass pass:android \
  --out build/yizhizuo-debug.apk build/aligned.apk
echo "BUILD OK -> build/yizhizuo-debug.apk"
