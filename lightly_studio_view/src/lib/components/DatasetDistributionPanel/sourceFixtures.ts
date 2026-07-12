import type { CategoryCount } from '$lib/components/BarChart';
import type { DistributionSource } from './types';
import { longTail } from '$lib/components/BarChart/fixtures';

/**
 * Prototype fixtures showing how the distribution panel generalises beyond
 * class labels. Each source produces the same `CategoryCount[]` shape, so the
 * existing bar-chart / sort / top-N / orientation UI is reused unchanged — only
 * the source of the counts differs. Used by Storybook to answer "how would this
 * extend to tags, metadata keys, or eval data?".
 */

function counts(entries: [string, number][]): CategoryCount[] {
    return entries.map(([label, count]) => ({ label, count }));
}

/** Distribution of samples across dataset tags. */
const tags: CategoryCount[] = counts([
    ['reviewed', 3820],
    ['train_split', 3110],
    ['hard_case', 1240],
    ['val_split', 640],
    ['to_relabel', 415],
    ['occluded', 288],
    ['blurry', 132],
    ['duplicate', 47]
]);

/** Several metadata keys, each with its own value distribution. */
const metadataWeather: CategoryCount[] = counts([
    ['clear', 4180],
    ['cloudy', 2260],
    ['rain', 980],
    ['fog', 410],
    ['snow', 190],
    ['night', 120]
]);

const metadataCamera: CategoryCount[] = counts([
    ['cam_front', 2600],
    ['cam_front_left', 1450],
    ['cam_front_right', 1420],
    ['cam_back', 1380],
    ['cam_back_left', 900],
    ['cam_back_right', 880]
]);

const metadataSplit: CategoryCount[] = counts([
    ['train', 6100],
    ['val', 1300],
    ['test', 740]
]);

/** Per-class evaluation metric (average precision, ×100 for readability). */
const evalAP: CategoryCount[] = counts([
    ['car', 91],
    ['person', 84],
    ['bicycle', 77],
    ['truck', 73],
    ['bus', 69],
    ['traffic_light', 58],
    ['stop_sign', 52],
    ['motorcycle', 44]
]);

/** Confusion / error counts from an eval run. */
const evalErrors: CategoryCount[] = counts([
    ['true_positive', 8420],
    ['false_positive', 1310],
    ['false_negative', 940],
    ['misclassified', 512],
    ['duplicate_pred', 176]
]);

/**
 * The full set of example sources. `class` uses the existing long-tail class
 * fixture; the others demonstrate tags, metadata (multi-key), and eval.
 */
export const exampleSources: DistributionSource[] = [
    {
        id: 'class',
        label: 'Class labels',
        data: longTail,
        valueNoun: 'annotations'
    },
    {
        id: 'tags',
        label: 'Tags',
        data: tags,
        valueNoun: 'samples'
    },
    {
        id: 'metadata',
        label: 'Metadata',
        groupLabel: 'Metadata key',
        valueNoun: 'samples',
        groups: [
            { id: 'weather', label: 'weather', data: metadataWeather },
            { id: 'camera_id', label: 'camera_id', data: metadataCamera },
            { id: 'split', label: 'split', data: metadataSplit }
        ]
    },
    {
        id: 'eval',
        label: 'Eval',
        groupLabel: 'Metric',
        groups: [
            { id: 'ap', label: 'AP per class (×100)', data: evalAP },
            { id: 'errors', label: 'Error breakdown', data: evalErrors }
        ]
    }
];
