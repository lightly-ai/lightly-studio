"""Compute COCO detection metrics for one prediction collection / subset pair."""

from __future__ import annotations

import io
import contextlib
from collections import defaultdict
from typing import Any
from uuid import UUID

import numpy as np
from sqlmodel import Session, col, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable, AnnotationType
from lightly_studio.models.annotation.object_detection import ObjectDetectionAnnotationTable
from lightly_studio.models.annotation_collection import AnnotationCollectionTable
from lightly_studio.models.annotation_label import AnnotationLabelTable
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


def _load_label_names(session: Session, label_ids: set[UUID]) -> dict[UUID, str]:
    """Batch-load annotation label names for a set of label IDs."""
    if not label_ids:
        return {}
    stmt = select(AnnotationLabelTable).where(
        col(AnnotationLabelTable.annotation_label_id).in_(label_ids)
    )
    rows = session.exec(stmt).all()
    return {row.annotation_label_id: row.annotation_label_name for row in rows}


def _iou(b1: tuple[int, int, int, int], b2: tuple[int, int, int, int]) -> float:
    """Compute IoU between two [x, y, w, h] boxes."""
    x1, y1, w1, h1 = b1
    x2, y2, w2, h2 = b2
    ix1, iy1 = max(x1, x2), max(y1, y2)
    ix2, iy2 = min(x1 + w1, x2 + w2), min(y1 + h1, y2 + h2)
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    union = w1 * h1 + w2 * h2 - inter
    return inter / union if union > 0 else 0.0


def _compute_confusion_matrix(
    session: Session,
    gt_anns: list[AnnotationBaseTable],
    pred_anns: list[AnnotationBaseTable],
    label_id_to_name: dict[UUID, str],
    iou_threshold: float,
    confidence_threshold: float,
) -> dict[str, Any]:
    """Build an n×n confusion matrix for matched GT/prediction pairs.

    Only matched pairs (IoU >= threshold) are counted; unmatched boxes are excluded.
    Rows = GT class, columns = predicted class.
    """
    gt_by_image: dict[UUID, list[AnnotationBaseTable]] = defaultdict(list)
    for ann in gt_anns:
        gt_by_image[ann.parent_sample_id].append(ann)

    pred_by_image: dict[UUID, list[AnnotationBaseTable]] = defaultdict(list)
    for ann in pred_anns:
        if (ann.confidence or 0.0) >= confidence_threshold:
            pred_by_image[ann.parent_sample_id].append(ann)

    label_names = sorted(
        {label_id_to_name.get(ann.annotation_label_id, str(ann.annotation_label_id)) for ann in gt_anns}
    )
    n = len(label_names)
    if n == 0:
        return {"labels": [], "matrix": []}

    name_to_idx = {name: idx for idx, name in enumerate(label_names)}
    matrix: list[list[int]] = [[0] * n for _ in range(n)]

    for image_id, image_gt_anns in gt_by_image.items():
        gt_bboxes = [(ann, _load_bbox(session, ann.sample_id)) for ann in image_gt_anns]
        image_pred_anns = sorted(
            pred_by_image.get(image_id, []),
            key=lambda a: a.confidence or 0.0,
            reverse=True,
        )
        pred_bboxes = [(ann, _load_bbox(session, ann.sample_id)) for ann in image_pred_anns]

        matched_gt: set[int] = set()

        for pred_ann, pred_bbox in pred_bboxes:
            if pred_bbox is None:
                continue
            best_iou, best_gi = iou_threshold - 1e-10, -1
            for gi, (_, gt_bbox) in enumerate(gt_bboxes):
                if gi in matched_gt or gt_bbox is None:
                    continue
                iou = _iou(pred_bbox, gt_bbox)
                if iou > best_iou:
                    best_iou, best_gi = iou, gi

            if best_gi < 0:
                continue

            gt_ann = gt_bboxes[best_gi][0]
            gt_name = label_id_to_name.get(gt_ann.annotation_label_id, str(gt_ann.annotation_label_id))
            pred_name = label_id_to_name.get(pred_ann.annotation_label_id, str(pred_ann.annotation_label_id))
            gi_idx = name_to_idx.get(gt_name, -1)
            pi_idx = name_to_idx.get(pred_name, -1)
            if gi_idx >= 0 and pi_idx >= 0:
                matrix[gi_idx][pi_idx] += 1
            matched_gt.add(best_gi)

    return {"labels": label_names, "matrix": matrix}


def _extract_per_class_metrics(
    evaluator: Any,
    label_to_cat_id: dict[UUID, int],
    label_id_to_name: dict[UUID, str],
) -> dict[str, Any]:
    """Extract per-category AP and recall from a COCOeval object after accumulate().

    Returns a dict mapping class name → {ap, recall, f1}.
    Uses area=all (index 0), maxDets=100 (index 2), first IoU threshold.
    """
    cat_id_to_label_id = {v: k for k, v in label_to_cat_id.items()}
    cat_ids = evaluator.params.catIds  # sorted list used during evaluation

    prec_arr = evaluator.eval["precision"]  # [T, R, K, A, M]
    rec_arr = evaluator.eval["recall"]       # [T, K, A, M]

    per_class: dict[str, Any] = {}
    for k, cat_id in enumerate(cat_ids):
        label_id = cat_id_to_label_id.get(cat_id)
        if label_id is None:
            continue
        class_name = label_id_to_name.get(label_id, str(label_id))

        prec_k = prec_arr[0, :, k, 0, 2]  # precision over recall thresholds
        valid_prec = prec_k[prec_k >= 0]
        ap = float(np.mean(valid_prec)) if valid_prec.size > 0 else 0.0

        rec_k = rec_arr[0, k, 0, 2]
        recall = float(rec_k) if not np.isnan(rec_k) else 0.0

        f1 = 2 * ap * recall / (ap + recall) if (ap + recall) > 0 else 0.0

        per_class[class_name] = {
            "ap": round(ap, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        }

    return per_class


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
) -> dict[str, Any]:
    """Compute COCO metrics for one (prediction collection, subset) pair.

    Returns a dict with keys: precision, recall, f1, mAP, avg_confidence, confusion_matrix.
    """
    gt_anns = _load_annotations(session, gt_collection.collection_id, tag_id)
    pred_anns = _load_annotations(session, pred_collection.collection_id, tag_id)

    if not gt_anns:
        return {
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "mAP": 0.0,
            "avg_confidence": 0.0,
            "confusion_matrix": {"labels": [], "matrix": []},
            "per_class_metrics": {},
        }

    # Build shared label → category_id map from GT labels
    all_label_ids = {ann.annotation_label_id for ann in gt_anns} | {
        ann.annotation_label_id for ann in pred_anns
    }
    label_to_cat_id = {lid: idx + 1 for idx, lid in enumerate(sorted(all_label_ids, key=str))}

    # Build shared parent_sample_id → integer image_id map
    all_parent_ids = {ann.parent_sample_id for ann in gt_anns}
    image_id_map = {pid: idx + 1 for idx, pid in enumerate(sorted(all_parent_ids, key=str))}

    # Load human-readable label names for confusion matrix
    label_id_to_name = _load_label_names(session, all_label_ids)

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
            confusion = _compute_confusion_matrix(
                session, gt_anns, pred_anns, label_id_to_name, iou_threshold, confidence_threshold
            )
            return {
                "precision": 0.0,
                "recall": 0.0,
                "f1": 0.0,
                "mAP": 0.0,
                "avg_confidence": 0.0,
                "confusion_matrix": confusion,
                "per_class_metrics": {},
            }

        coco_dt = coco_gt.loadRes(dt_list)
        evaluator = COCOeval(coco_gt, coco_dt, iouType="bbox")
        evaluator.params.iouThrs = np.array([iou_threshold])
        evaluator.evaluate()
        evaluator.accumulate()
        evaluator.summarize()

    per_class = _extract_per_class_metrics(evaluator, label_to_cat_id, label_id_to_name)
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

    confusion = _compute_confusion_matrix(
        session, gt_anns, pred_anns, label_id_to_name, iou_threshold, confidence_threshold
    )

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "mAP": round(map_score, 4),
        "avg_confidence": round(avg_confidence, 4),
        "confusion_matrix": confusion,
        "per_class_metrics": per_class,
    }
