import { NO_GROUND_TRUTH_ROW_LABEL, NO_PREDICTION_COL_LABEL, type ConfusionMatrix } from './types';

/**
 * Storybook fixtures. The shapes match what the endpoint endpoint returns
 */

const fp = NO_GROUND_TRUTH_ROW_LABEL;
const fn = NO_PREDICTION_COL_LABEL;

function matrix(real: string[], counts: number[][]): ConfusionMatrix {
    return {
        row_labels: [...real, fp],
        col_labels: [...real, fn],
        counts
    };
}

export const small3Classes: ConfusionMatrix = matrix(
    ['bike', 'car', 'person'],
    [
        [42, 1, 2, 5],
        [0, 88, 4, 7],
        [3, 6, 156, 21],
        [2, 4, 8, 0]
    ]
);

export const medium8Classes: ConfusionMatrix = matrix(
    ['bike', 'car', 'chair', 'cup', 'dog', 'knife', 'person', 'sink'],
    [
        [85, 1, 0, 0, 0, 0, 2, 0, 8],
        [0, 220, 0, 0, 1, 0, 3, 0, 12],
        [0, 0, 28, 0, 0, 0, 1, 0, 4],
        [0, 0, 1, 38, 0, 0, 0, 0, 6],
        [0, 2, 0, 0, 42, 0, 1, 0, 5],
        [0, 0, 0, 1, 0, 18, 0, 0, 3],
        [2, 4, 0, 0, 1, 0, 180, 0, 20],
        [0, 0, 0, 0, 0, 0, 0, 12, 3],
        [3, 9, 1, 2, 2, 0, 7, 1, 0]
    ]
);

const large20RealLabels = [
    'apple',
    'backpack',
    'bicycle',
    'bird',
    'boat',
    'book',
    'bottle',
    'bowl',
    'car',
    'cat',
    'chair',
    'clock',
    'cup',
    'dog',
    'fork',
    'horse',
    'keyboard',
    'knife',
    'laptop',
    'person'
];

export const large20Classes: ConfusionMatrix = (() => {
    const n = large20RealLabels.length;
    const rng = mulberry32(42);
    const counts: number[][] = [];
    for (let i = 0; i <= n; i++) {
        const row: number[] = [];
        for (let j = 0; j <= n; j++) {
            if (i === n && j === n) {
                row.push(0);
            } else if (i === j && i < n) {
                row.push(20 + Math.floor(rng() * 200));
            } else if (j === n || i === n) {
                row.push(Math.floor(rng() * 18));
            } else {
                row.push(rng() < 0.18 ? Math.floor(rng() * 6) : 0);
            }
        }
        counts.push(row);
    }
    return matrix(large20RealLabels, counts);
})();

// prettier-ignore
const coco80RealLabels = [
    'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck', 'boat',
    'traffic light', 'fire hydrant', 'stop sign', 'parking meter', 'bench', 'bird', 'cat', 'dog',
    'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra', 'giraffe', 'backpack', 'umbrella',
    'handbag', 'tie', 'suitcase', 'frisbee', 'skis', 'snowboard', 'sports ball', 'kite',
    'baseball bat', 'baseball glove', 'skateboard', 'surfboard', 'tennis racket', 'bottle',
    'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple', 'sandwich',
    'orange', 'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake', 'chair', 'couch',
    'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse', 'remote',
    'keyboard', 'cell phone', 'microwave', 'oven', 'toaster', 'sink', 'refrigerator', 'book',
    'clock', 'vase', 'scissors', 'teddy bear', 'hair drier', 'toothbrush'
];

/**
 * COCO-like 80-class fixture for the large-class-count edge case (LIG-9665).
 * Confusion is concentrated between semantically adjacent labels (|i - j| <= 2)
 * to mimic real OD confusion clusters (e.g. car/truck/bus, fork/knife/spoon).
 */
export const coco80Classes: ConfusionMatrix = (() => {
    const n = coco80RealLabels.length;
    const rng = mulberry32(7);
    const counts: number[][] = [];
    for (let i = 0; i <= n; i++) {
        const row: number[] = [];
        for (let j = 0; j <= n; j++) {
            if (i === n && j === n) {
                row.push(0);
            } else if (i === j && i < n) {
                row.push(10 + Math.floor(rng() * 300));
            } else if (i === n || j === n) {
                row.push(rng() < 0.6 ? Math.floor(rng() * 25) : 0);
            } else if (Math.abs(i - j) <= 2) {
                row.push(rng() < 0.5 ? Math.floor(rng() * 40) : 0);
            } else {
                row.push(rng() < 0.04 ? Math.floor(rng() * 8) : 0);
            }
        }
        counts.push(row);
    }
    return matrix(coco80RealLabels, counts);
})();

export const empty: ConfusionMatrix = {
    row_labels: [],
    col_labels: [],
    counts: []
};

export const singleClass: ConfusionMatrix = matrix(
    ['person'],
    [
        [142, 18],
        [11, 0]
    ]
);

function mulberry32(seed: number): () => number {
    let state = seed >>> 0;
    return () => {
        state = (state + 0x6d2b79f5) | 0;
        let t = state;
        t = Math.imul(t ^ (t >>> 15), t | 1);
        t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
}
