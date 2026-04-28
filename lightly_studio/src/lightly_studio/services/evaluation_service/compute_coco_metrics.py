"""Compute COCO detection metrics for one prediction collection / subset pair."""

from __future__ import annotations

import io
import contextlib
from typing import Any
from uuid import UUID

import numpy as np
from sqlmodel import Session, col, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable, AnnotationType
from lightly_studio.models.annotation.object_detection import ObjectDetectionAnnotationTable
from lightly_studio.models.annotation_collection import AnnotationCollectionTable
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.sample import SampleTagLinkTable


def _load_annotations(
    session: Session,
    annotation_collection_id: UUID,
    tag_id: UUID | None,
) -> list[AnnotationBaseTable]:
    """Load all OD annotations for an annotation collection, optionally filtered by tag.

    Tag filtering: keep annotations whose *parent* sample carries the given tag.
    """
    stmt = (
        select(AnnotationBaseTable)
        .join(SampleTable, col(SampleTable.sample_id) == col(AnnotationBaseTable.sample_id))
        .where(col(SampleTable.collection_id) == annotation_collection_id)
        .where(col(AnnotationBaseTable.annotation_type) == AnnotationType.OBJECT_DETECTION)
    )
    if tag_id is not None:
        stmt = stmt.join(
            SampleTagLinkTable,
            col(SampleTagLinkTable.sample_id) == col(AnnotationBaseTable.parent_sample_id),
        ).where(col(SampleTagLinkTable.tag_id) == tag_id)

    return list(session.exec(stmt).all())


def _load_bbox(
    session: Session,
    sample_id: UUID,
) -> tuple[int, int, int, int] | None:
    """Return [x, y, w, h] for an OD annotation sample, or None."""
    row = session.get(ObjectDetectionAnnotationTable, sample_id)
    if row is None:
        return None
    return (row.x, row.y, row.width, row.height)


def _load_parent_image(session: Session, parent_sample_id: UUID) -> ImageTable | None:
    return session.get(ImageTable, parent_sample_id)


def _build_coco_gt(
    session: Session,
    gt_annotations: list[AnnotationBaseTable],
    label_to_cat_id: dict[UUID, int],
    image_id_map: dict[UUID, int],
) -> dict[str, Any]:
    """Build a COCO-format GT dict from annotation records."""
    images = []
    annotations = []
    seen_images: set[UUID] = set()

    for ann in gt_annotations:
        parent_id = ann.parent_sample_id
        if parent_id not in seen_images:
            img = _load_parent_image(session, parent_id)
            if img is not None:
                images.append(
                    {
                        "id": image_id_map[parent_id],
                        "width": img.width,
                        "height": img.height,
                        "file_name": img.file_name,
                    }
                )
            seen_images.add(parent_id)

        bbox = _load_bbox(session, ann.sample_id)
        if bbox is None:
            continue
        x, y, w, h = bbox
        annotations.append(
            {
                "id": len(annotations) + 1,
                "image_id": image_id_map[parent_id],
                "category_id": label_to_cat_id[ann.annotation_label_id],
                "bbox": [x, y, w, h],
                "area": w * h,
                "iscrowd": 0,
            }
        )

    categories = [{"id": cid, "name": str(lid)} for lid, cid in label_to_cat_id.items()]
    return {"images": images, "annotations": annotations, "categories": categories}


def _build_coco_dt(
    pred_annotations: list[AnnotationBaseTable],
    label_to_cat_id: dict[UUID, int],
    image_id_map: dict[UUID, int],
    session: Session,
    confidence_threshold: float,
) -> list[dict[str, Any]]:
    """Build a COCO-format results list from prediction annotation records."""
    results = []
    for ann in pred_annotations:
        score = ann.confidence or 0.0
        if score < confidence_threshold:
            continue
        bbox = _load_bbox(session, ann.sample_id)
        if bbox is None:
            continue
        x, y, w, h = bbox
        results.append(
            {
                "image_id": image_id_map.get(ann.parent_sample_id, -1),
                "category_id": label_to_cat_id.get(ann.annotation_label_id, -1),
                "bbox": [x, y, w, h],
                "score": score,
            }
        )
    return [r for r in results if r["image_id"] != -1 and r["category_id"] != -1]


def compute_metrics_for_pair(
    session: Session,
    gt_collection: AnnotationCollectionTable,
    pred_collection: AnnotationCollectionTable,
    tag_id: UUID | None,
    iou_threshold: float,
    confidence_threshold: float,
) -> dict[str, float]:
    """Compute COCO metrics for one (prediction collection, subset) pair.

    Returns a dict with keys: precision, recall, f1, mAP, avg_confidence.
    """
    gt_anns = _load_annotations(session, gt_collection.collection_id, tag_id)
    pred_anns = _load_annotations(session, pred_collection.collection_id, tag_id)

    if not gt_anns:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0, "mAP": 0.0, "avg_confidence": 0.0}

    # Build shared label → category_id map from GT labels
    all_label_ids = {ann.annotation_label_id for ann in gt_anns} | {
        ann.annotation_label_id for ann in pred_anns
    }
    label_to_cat_id = {lid: idx + 1 for idx, lid in enumerate(sorted(all_label_ids, key=str))}

    # Build shared parent_sample_id → integer image_id map
    all_parent_ids = {ann.parent_sample_id for ann in gt_anns}
    image_id_map = {pid: idx + 1 for idx, pid in enumerate(sorted(all_parent_ids, key=str))}

    gt_dict = _build_coco_gt(session, gt_anns, label_to_cat_id, image_id_map)
    dt_list = _build_coco_dt(
        pred_anns, label_to_cat_id, image_id_map, session, confidence_threshold
    )

    # Lazy import so pycocotools is only required when actually computing metrics.
    from pycocotools.coco import COCO  # noqa: PLC0415
    from pycocotools.cocoeval import COCOeval  # noqa: PLC0415

    # Load into pycocotools — suppress its stdout chatter
    with contextlib.redirect_stdout(io.StringIO()):
        coco_gt = COCO()
        coco_gt.dataset = gt_dict
        coco_gt.createIndex()

        if not dt_list:
            return {
                "precision": 0.0,
                "recall": 0.0,
                "f1": 0.0,
                "mAP": 0.0,
                "avg_confidence": 0.0,
            }

        coco_dt = coco_gt.loadRes(dt_list)
        evaluator = COCOeval(coco_gt, coco_dt, iouType="bbox")
        evaluator.params.iouThrs = np.array([iou_threshold])
        evaluator.evaluate()
        evaluator.accumulate()
        evaluator.summarize()

    stats = evaluator.stats  # [AP, AP50, AP75, APs, APm, APl, AR1, AR10, AR100, ARs, ARm, ARl]
    map_score = float(stats[0]) if not np.isnan(stats[0]) else 0.0
    recall = float(stats[8]) if not np.isnan(stats[8]) else 0.0  # AR@100 as proxy

    # COCO stores precision in evaluator.eval["precision"] and uses -1 for
    # entries without a valid value, so filter those out before averaging.
    precision_values = evaluator.eval["precision"]
    valid_precision_values = precision_values[precision_values >= 0]
    precision = (
        float(np.mean(valid_precision_values)) if valid_precision_values.size > 0 else 0.0
    )

    f1 = (
        2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    )
    avg_confidence = (
        float(np.mean([ann.confidence for ann in pred_anns if ann.confidence is not None]))
        if pred_anns
        else 0.0
    )

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "mAP": round(map_score, 4),
        "avg_confidence": round(avg_confidence, 4),
    }
