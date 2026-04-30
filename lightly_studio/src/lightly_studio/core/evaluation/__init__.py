"""Evaluation submodule: metrics computation, annotation ingestion, and result persistence."""

from lightly_studio.core.evaluation.add_predictions import add_predictions_from_coco
from lightly_studio.core.evaluation.add_predictions_lightly import add_predictions_from_lightly
from lightly_studio.core.evaluation.register_gt_collection import register_annotation_collection
from lightly_studio.core.evaluation.run_evaluation import run_evaluation

__all__ = [
    "add_predictions_from_coco",
    "add_predictions_from_lightly",
    "register_annotation_collection",
    "run_evaluation",
]
