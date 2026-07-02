import type { CategoryCount } from './types';

/**
 * Storybook fixtures. Shapes mirror the `annotation_type`-filtered count API
 * that LIG-9581 will wire up: one count per class label, sorted by count
 * descending (the order the panel is expected to request).
 */

function counts(entries: [string, number][]): CategoryCount[] {
    return entries.map(([label, count]) => ({ label, count }));
}

/** Few classes, similar counts. */
export const balanced: CategoryCount[] = counts([
    ['chair', 112],
    ['dog', 104],
    ['bike', 96],
    ['person', 91],
    ['car', 88]
]);

/** Many classes, one dominant class with an exponentially decaying tail. */
export const longTail: CategoryCount[] = [
    'person',
    'car',
    'chair',
    'bottle',
    'cup',
    'dog',
    'cat',
    'book',
    'bowl',
    'handbag',
    'umbrella',
    'bird',
    'boat',
    'truck',
    'bench',
    'backpack',
    'sheep',
    'cow',
    'laptop',
    'tv',
    'couch',
    'horse',
    'kite',
    'clock',
    'vase',
    'fork',
    'knife',
    'spoon',
    'toaster',
    'hair drier'
].map((label, index) => ({
    label,
    count: Math.max(1, Math.round(4200 * Math.exp(-0.35 * index)))
}));

// prettier-ignore
const coco80Labels = [
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

/** COCO-like 80-class fixture for the horizontal-scroll edge case. */
export const many80Classes: CategoryCount[] = (() => {
    const rng = mulberry32(42);
    return coco80Labels
        .map((label) => ({ label, count: 5 + Math.floor(rng() * 500) }))
        .sort((a, b) => b.count - a.count);
})();

/** Long class names to exercise axis-label truncation (tooltip shows the full name). */
export const longLabels: CategoryCount[] = counts([
    ['construction_vehicle_articulated_dump_truck', 320],
    ['pedestrian_walking_with_bicycle', 240],
    ['traffic_sign_speed_limit_temporary', 185],
    ['emergency_vehicle_ambulance', 96],
    ['road_obstacle_construction_barrier', 44],
    ['car', 410]
]);

export const singleClass: CategoryCount[] = counts([['person', 1423]]);

export const empty: CategoryCount[] = [];

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
