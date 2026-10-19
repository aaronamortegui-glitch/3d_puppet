@echo off
REM Creates server\.venv (Python 3.11) with PyTorch for CUDA 12.8 (RTX 50xx ready)
REM and the light server dependencies (MediaPipe, NLF, MoGe-2 focal estimation).
setlocal
cd /d %~dp0
set PY=py -3.11
%PY% --version >nul 2>&1 || set PY="C:\Program Files\Python311\python.exe"
if not exist .venv (
  %PY% -m venv .venv || goto :err
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128 || goto :err
python -m pip install -r requirements.txt || goto :err
python -c "import torch;print('torch',torch.__version__,'cuda',torch.cuda.is_available())"
echo.
echo Done. Optional: install_sam3d.bat for SAM 3D Body (needs Hugging Face access).
echo Start the server with run_server.bat
exit /b 0
:err
echo INSTALL FAILED
exit /b 1
