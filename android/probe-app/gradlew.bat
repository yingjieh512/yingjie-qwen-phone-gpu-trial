@echo off
where gradle >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  gradle %*
  exit /b %ERRORLEVEL%
)

echo Gradle is not installed and this repository does not vendor a Gradle wrapper jar. 1>&2
echo. 1>&2
echo Install Android Studio or Gradle with the Android Gradle Plugin available, then run: 1>&2
echo   gradle assembleDebug 1>&2
echo. 1>&2
echo Or open android\probe-app in Android Studio and build the app module. 1>&2
echo Expected APK: 1>&2
echo   app\build\outputs\apk\debug\app-debug.apk 1>&2
exit /b 127
