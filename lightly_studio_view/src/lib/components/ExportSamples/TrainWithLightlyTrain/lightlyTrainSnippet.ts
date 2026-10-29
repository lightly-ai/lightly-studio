/** Docs page that walks from an export with images to a trained detector and back. */
export const TRAIN_WITH_LIGHTLYTRAIN_DOCS_URL =
    'https://docs.lightly.ai/studio/workflows/train_with_lightlytrain/';

/** Trains a LightlyTrain detector on the unzipped `coco_export.zip`. */
export const LIGHTLYTRAIN_SNIPPET = `# pip install lightly-train
import lightly_train

lightly_train.train_object_detection(
    out="out/detector",
    model="ltdetrv2-s-coco",
    data={
        "format": "coco",
        "train": {
            "annotations": "coco_export/annotations.json",
            "images": "coco_export/images",
        },
        # For a real validation set, export a separate tag, e.g. "val".
        "val": {
            "annotations": "coco_export/annotations.json",
            "images": "coco_export/images",
        },
    },
)
`;
