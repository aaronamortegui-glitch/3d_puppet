@echo off
REM Optional: SAM 3D Body (Meta). Requires:
REM   1) access granted to https://huggingface.co/facebook/sam-3d-body-dinov3
REM   2) "hf auth login" done once (token stored in your user profile)
REM detectron2 is NOT needed: the server feeds person boxes from torchvision.
setlocal
cd /d %~dp0
call .venv\Scripts\activate.bat || goto :err
if not exist vendor mkdir vendor
if not exist vendor\sam-3d-body (
  git clone https://github.com/facebookresearch/sam-3d-body.git vendor\sam-3d-body || goto :err
)
python -m pip install pytorch-lightning opencv-python yacs scikit-image einops timm dill pandas rich hydra-core pyrootutils roma joblib loguru optree fvcore huggingface_hub networkx==3.2.1 omegaconf trimesh || goto :err
python -m pip install git+https://github.com/microsoft/MoGe.git || goto :err
python -c "from huggingface_hub import snapshot_download as s; s('facebook/sam-3d-body-dinov3')" || goto :hf
echo SAM 3D Body ready.
exit /b 0
:hf
echo Could not download the checkpoint: request access on Hugging Face and run "hf auth login".
exit /b 1
:err
echo INSTALL FAILED
exit /b 1
