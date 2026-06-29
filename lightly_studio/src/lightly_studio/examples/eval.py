from ultralytics import YOLO

import lightly_studio as ls
from lightly_studio.core.annotation import CreateObjectDetection
from lightly_studio.core.dataset_query import (
    AND,
    EvaluationMetricField,
    ImageSampleField,
    SampleEvaluationQuery,
)
from lightly_studio.core.dataset_query.object_detection_query import (
    ObjectDetectionField,
    ObjectDetectionQuery,
)
from lightly_studio.evaluation.image_dataset_evaluate import ObjectDetectionEvaluationConfig

image_path = r"D:\\01_work\\pkg\\dataset_examples\\coco_subset_128_images\\images"

# we should explore both options - predict using code and predict using plugins in studio


def yolo_box_to_annotation(box, class_names: dict[int, str]) -> CreateObjectDetection:
    """Convert a single Ultralytics box to a Lightly object-detection annotation."""
    cls_id = int(box.cls)
    x, y, w, h = box.xywh[0].tolist()

    return CreateObjectDetection(
        class_name=class_names[cls_id],
        x=round(x - w / 2),
        y=round(y - h / 2),
        width=max(1, round(w)),
        height=max(1, round(h)),
        confidence=float(box.conf),
    )

def predict_using_yolo26(
    dataset: ls.ImageDataset,
    model_name: str = "yolo26n.pt",
    conf: float = 0.25,
) -> int:
    model = YOLO(model_name)
    annotation_source = f"{model_name}_prediction"
    total_annotations = 0

    for sample in dataset:
        result = model.predict(source=sample.file_path_abs, conf=conf, verbose=False)[0]
        annotations = [
            yolo_box_to_annotation(box, result.names)
            for box in (result.boxes or [])
        ]
        if annotations:
            sample.add_annotations(
                annotations=annotations,
                annotation_source=annotation_source,
            )
            total_annotations += len(annotations)
    return total_annotations

#do the process simpler  -  not restart a few times for each step

def main():
    ls.db_manager.connect(cleanup_existing=True)
    dataset = ls.ImageDataset.load_or_create()
    dataset.add_images_from_path(path=image_path)
    #add ground truth annotations
    dataset.add_annotations_from_coco(
        annotations_json=r"D:\01_work\pkg\dataset_examples\coco_subset_128_images\instances_train2017.json",
        images_root=image_path,
        annotation_source="ground_truth",
    )
    #add predictions
    predict_using_yolo26(dataset)
    dataset.evaluate().object_detection(
        name="gt_yolo26n",
        gt_annotation_source="ground_truth",
        pred_annotation_source="yolo26n.pt_prediction",
        config=ObjectDetectionEvaluationConfig(
            iou_threshold=0.5,
            classwise=True,
        ),
    )

    dataset.evaluate().object_detection(
        name="gt_yolo26n_0.8",
        gt_annotation_source="ground_truth",
        pred_annotation_source="yolo26n.pt_prediction",
        config=ObjectDetectionEvaluationConfig(
            iou_threshold=0.8,
            classwise=True,
        ),
    )
    #tag samples that have fp > 0
    expr = SampleEvaluationQuery(
        "gt_yolo26n",
        EvaluationMetricField("fp") > 0,
    )
    dataset.query().match(expr).add_tag("fp_gt_yolo26n")

    #tag samples that have fn > 0
    expr = SampleEvaluationQuery(
        "gt_yolo26n",
        EvaluationMetricField("fn") > 0,
    )
    dataset.query().match(expr).add_tag("fn_gt_yolo26n")

    query = dataset.query().match(
    AND(
        ImageSampleField.tags.contains("fp_gt_yolo26n"),
        ObjectDetectionQuery(ObjectDetectionField.source == "yolo26n.pt_prediction"),
    )
)
    dataset.export(query).to_coco_object_detections(
        output_json="exports/fp_gt_yolo26n.coco.json"
    )

    query = dataset.query().match(
    AND(
        ImageSampleField.tags.contains("fn_gt_yolo26n"),
        ObjectDetectionQuery(ObjectDetectionField.source == "yolo26n.pt_prediction"),
    )
)
    dataset.export(query).to_coco_object_detections(
        output_json="exports/fn_gt_yolo26n.coco.json"
    )

    ls.start_gui()


if __name__ == "__main__":

    main()
