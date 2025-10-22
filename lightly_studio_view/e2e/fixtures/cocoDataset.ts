/**
 * COCO-128 Dataset Test Fixture
 *
 * This fixture defines the expected properties of the COCO-128 dataset
 * used in E2E tests. Only includes labels and values actively used in tests.
 *
 * Note: These values are based on the actual COCO-128 dataset in
 * lightly_studio/datasets/coco-128/ and should match reality.
 */

/**
 * Dataset-level constants
 */
export const cocoDataset = {
    /** Total number of samples in the dataset */
    totalSamples: 128,

    /** Total number of unique labels in the dataset */
    totalLabels: 71,

    /** Default page size when loading samples */
    defaultPageSize: 100,

    /** Expected filename when exporting annotations */
    exportFilename: 'coco_export.json',

    /** Labels actively used in tests with their sample/annotation counts */
    labels: {
        airplane: {
            name: 'airplane',
            /** Total samples containing this label */
            sampleCount: 7,
            /** Total annotations with this label */
            annotationCount: 12,
            /** Position in alphabetically sorted label list */
            sortedIndex: 0
        },
        apple: {
            name: 'apple',
            sampleCount: 2,
            annotationCount: 2,
            sortedIndex: 1
        },
        backpack: {
            name: 'backpack',
            sampleCount: 1,
            annotationCount: 1
        },
        baseballBat: {
            name: 'baseball bat',
            sampleCount: 2,
            annotationCount: 2
        },
        baseballGlove: {
            name: 'baseball glove',
            sampleCount: 3,
            annotationCount: 3
        },
        bear: {
            name: 'bear',
            sampleCount: 2,
            annotationCount: 3
        },
        book: {
            name: 'book',
            sampleCount: 3,
            annotationCount: 6
        },
        car: {
            name: 'car',
            sampleCount: 21,
            annotationCount: 21,
            sortedIndex: 17
        },
        cat: {
            name: 'cat',
            sampleCount: 4,
            annotationCount: 5
        },
        cellPhone: {
            name: 'cell phone',
            sampleCount: 8,
            annotationCount: 8,
        },
        chair: {
            name: 'chair',
            sampleCount: 10,
            annotationCount: 10
        },
        dog: {
            name: 'dog',
            sampleCount: 5,
            annotationCount: 5
        },
        donut: {
            name: 'donut',
            sampleCount: 1,
            annotationCount: 1
        },
        person: {
            name: 'person',
            sampleCount: 61,
            annotationCount: 67
        },
        tie: {
            name: 'tie',
            sampleCount: 3,
            annotationCount: 3
        },
        zebra: {
            name: 'zebra',
            sampleCount: 3,
            annotationCount: 3,
            sortedIndex: 70
        }
    }
} as const;

/**
 * Type helper for label names
 */
export type CocoLabelName = keyof typeof cocoDataset.labels;
