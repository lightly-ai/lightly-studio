import { buildPairRows } from './pairRows';

const count = (source: string, label: string) => ({
    annotation_collection_id: source,
    annotation_label_id: `${source}-${label}`,
    label_name: label,
    current_count: 1,
    total_count: 2
});

export const TEST_SOURCES = [
    { id: 'gt', name: 'ground_truth' },
    { id: 'model', name: 'model_v1.2' }
];

/** ground_truth: car, Deer. model_v1.2: Deer, raccoon. */
export const testRows = (unticked: Parameters<typeof buildPairRows>[2] = []) =>
    buildPairRows(
        TEST_SOURCES,
        [
            count('gt', 'Deer'),
            count('gt', 'car'),
            count('model', 'raccoon'),
            count('model', 'Deer')
        ],
        unticked
    );
