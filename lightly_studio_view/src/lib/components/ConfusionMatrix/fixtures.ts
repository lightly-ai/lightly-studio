import {
    NO_GROUND_TRUTH_ROW_LABEL,
    NO_PREDICTION_COL_LABEL,
    type AnnotationPairing,
    type ConfusionMatrix
} from './types';

/**
 * Storybook fixtures. The shapes match what the LIG-9514 endpoint returns
 * (sorted real classes, then synthetic FP row / FN column).
 *
 * Pairing fixtures drive the threshold-slider story; the matrix is rebuilt
 * client-side from them via `buildConfusionMatrix`.
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

/** Coco-like raw pairings for the client-side threshold story. */
export const cocoLikePairings: AnnotationPairing[] = (() => {
    const classes = ['bicycle', 'car', 'dog', 'person', 'traffic light'];
    const rng = mulberry32(7);
    const out: AnnotationPairing[] = [];
    for (const cls of classes) {
        for (let i = 0; i < 60; i++) {
            const confused = rng() < 0.08;
            const predCls = confused ? classes[Math.floor(rng() * classes.length)] : cls;
            out.push({
                gt_label: cls,
                pred_label: predCls,
                confidence: 0.4 + rng() * 0.6,
                iou: 0.45 + rng() * 0.5
            });
        }
        for (let i = 0; i < 6; i++) {
            out.push({
                gt_label: null,
                pred_label: cls,
                confidence: 0.2 + rng() * 0.6,
                iou: null
            });
        }
        for (let i = 0; i < 5; i++) {
            out.push({
                gt_label: cls,
                pred_label: null,
                confidence: null,
                iou: null
            });
        }
        for (let i = 0; i < 8; i++) {
            out.push({
                gt_label: cls,
                pred_label: cls,
                confidence: 0.05 + rng() * 0.18,
                iou: 0.3 + rng() * 0.6
            });
        }
        for (let i = 0; i < 4; i++) {
            out.push({
                gt_label: cls,
                pred_label: cls,
                confidence: 0.5 + rng() * 0.4,
                iou: 0.05 + rng() * 0.35
            });
        }
    }
    return out;
})();

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
