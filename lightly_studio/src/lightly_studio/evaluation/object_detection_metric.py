"""Object detection evaluation metric primitives."""

from __future__ import annotations

import numpy as np


def compute_iou_matrix(pred_corners: np.ndarray, gt_corners: np.ndarray) -> np.ndarray:
    """Compute pairwise IoU from corner arrays.

    Args:
        pred_corners: Array of shape (P, 4) with [x1, y1, x2, y2] per prediction.
        gt_corners: Array of shape (G, 4) with [x1, y1, x2, y2] per ground truth.

    Returns:
        IoU matrix of shape (P, G), or an empty array if either input is empty.
    """
    if pred_corners.size == 0 or gt_corners.size == 0:
        return np.empty((len(pred_corners), len(gt_corners)))

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

    return inter / union  # (P, G)
