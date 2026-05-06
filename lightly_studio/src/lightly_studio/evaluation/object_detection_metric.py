"""Object detection evaluation metric primitives."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


def compute_iou_matrix(
    pred_corners: NDArray[np.int64],
    gt_corners: NDArray[np.int64],
) -> NDArray[np.float64]:
    """Compute pairwise IoU from corner arrays.

    Args:
        pred_corners: (P, 4) array of [x1, y1, x2, y2] prediction boxes in image pixel coordinates.
        gt_corners: (G, 4) array of [x1, y1, x2, y2] ground-truth boxes in image pixel coordinates.

    Returns:
        IoU matrix of shape (P, G), or an empty array if either input is empty.
    """
    if pred_corners.size == 0 or gt_corners.size == 0:
        return np.empty((len(pred_corners), len(gt_corners)), dtype=np.float64)

    inter_x1 = np.maximum(pred_corners[:, None, 0], gt_corners[None, :, 0])
    inter_y1 = np.maximum(pred_corners[:, None, 1], gt_corners[None, :, 1])
    inter_x2 = np.minimum(pred_corners[:, None, 2], gt_corners[None, :, 2])
    inter_y2 = np.minimum(pred_corners[:, None, 3], gt_corners[None, :, 3])

    inter = np.maximum(0, inter_x2 - inter_x1) * np.maximum(0, inter_y2 - inter_y1)
    pred_area = (pred_corners[:, 2] - pred_corners[:, 0]) * (
        pred_corners[:, 3] - pred_corners[:, 1]
    )
    gt_area = (gt_corners[:, 2] - gt_corners[:, 0]) * (gt_corners[:, 3] - gt_corners[:, 1])
    union = pred_area[:, None] + gt_area[None, :] - inter

    iou = inter / union
    return np.asarray(np.nan_to_num(iou, nan=0.0), dtype=np.float64)  # (P, G)
