"""Person detector (torchvision Faster R-CNN v2, BSD) - avoids building
detectron2 on Windows.  Returns boxes [x0, y0, x1, y1] sorted by area."""

import numpy as np

_det = None


def person_boxes(rgb, thr=0.6, max_people=1):
    global _det
    import torch
    from torchvision.models.detection import (FasterRCNN_ResNet50_FPN_V2_Weights,
                                              fasterrcnn_resnet50_fpn_v2)
    if _det is None:
        _det = fasterrcnn_resnet50_fpn_v2(
            weights=FasterRCNN_ResNet50_FPN_V2_Weights.DEFAULT).cuda().eval()
    t = torch.from_numpy(rgb).permute(2, 0, 1).float().div(255).cuda()
    with torch.no_grad():
        out = _det([t])[0]
    keep = (out["labels"] == 1) & (out["scores"] >= thr)
    boxes = out["boxes"][keep].cpu().numpy()
    if not len(boxes):
        h, w = rgb.shape[:2]
        return np.array([[0, 0, w, h]], dtype=np.float32)
    area = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
    return boxes[np.argsort(-area)][:max_people].astype(np.float32)
