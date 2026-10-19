@echo off
REM Process every photo in a folder, without Claude or any cloud service:
REM   1) pose server estimates pose + camera for each photo  -> JSON
REM   2) Blender builds one .blend per photo (puppet + camera + photo background)
REM      and an overlay PNG to check the fit.
REM
REM usage: run_samples.bat [photos_dir] [method]     method: auto | nlf | mediapipe | sam3d_body
setlocal
cd /d %~dp0..
set PHOTOS=%~1
if "%PHOTOS%"=="" set PHOTOS=samples\photos
set METHOD=%~2
if "%METHOD%"=="" set METHOD=auto
set OUT=samples\results
set BLENDER="C:\Program Files\Blender Foundation\Blender 5.0\blender.exe"
if not "%BLENDER_EXE%"=="" set BLENDER="%BLENDER_EXE%"

server\.venv\Scripts\python.exe server\pose_server.py --batch "%PHOTOS%" --out "%OUT%" --method %METHOD% || goto :err
%BLENDER% -b --factory-startup --python tools\blender_batch.py -- "%OUT%" || goto :err
echo.
echo Done. Open the .blend files in %OUT% (camera view: Numpad 0).
exit /b 0
:err
echo FAILED
exit /b 1
