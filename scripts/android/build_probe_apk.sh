#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROJECT_DIR="$ROOT_DIR/android/probe-app"
APK_PATH="$PROJECT_DIR/app/build/outputs/apk/debug/app-debug.apk"

if [[ ! -d "$PROJECT_DIR" ]]; then
  echo "error: Android probe project not found: $PROJECT_DIR" >&2
  exit 2
fi

echo "QPNPU probe app project: $PROJECT_DIR"
echo "Expected debug APK: $APK_PATH"

cd "$PROJECT_DIR"

if [[ -x "./gradlew" ]]; then
  ./gradlew assembleDebug
elif [[ -f "./gradlew" ]]; then
  bash ./gradlew assembleDebug
elif [[ -f "./gradlew.bat" ]] && command -v cmd.exe >/dev/null 2>&1; then
  cmd.exe /c gradlew.bat assembleDebug
elif command -v gradle >/dev/null 2>&1; then
  gradle assembleDebug
else
  cat >&2 <<EOF
No Gradle runner was found.

Install Android Studio or Gradle with the Android Gradle Plugin available, then build with one of:
  cd android/probe-app && gradle assembleDebug
  cd android/probe-app && ./gradlew assembleDebug
  cd android/probe-app && .\\gradlew.bat assembleDebug

You can also open android/probe-app in Android Studio and build the app module.
Expected APK:
  $APK_PATH
EOF
  exit 127
fi

if [[ -f "$APK_PATH" ]]; then
  echo "Built debug APK: $APK_PATH"
else
  echo "Build command finished, but expected APK was not found: $APK_PATH" >&2
  exit 1
fi
