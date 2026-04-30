"""Evaluation submodule: metrics computation, annotation ingestion, and result persistence."""

from lightly_studio.core.evaluation.register_gt_collection import register_annotation_collection
from lightly_studio.core.evaluation.run_evaluation import run_evaluation

__all__ = [
    "register_annotation_collection",
    "run_evaluation",
]
