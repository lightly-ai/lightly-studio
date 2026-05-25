<script module lang="ts">
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import { fn } from 'storybook/test';
    import type { EvaluationRunView } from '$lib/api/lightly_studio_local/types.gen';
    import EvaluationRunsPanel from './EvaluationRunsPanel.svelte';

    const sampleRuns: EvaluationRunView[] = [
        {
            id: 'run-1',
            name: 'Baseline detector',
            evaluation_run_configuration: {
                model: 'yolov8n',
                checkpoint: 'yolov8n.pt',
                dataset: 'coco-val-2017',
                dataset_split: 'val',
                image_size: 640,
                batch_size: 32,
                iou_threshold: 0.5,
                confidence_threshold: 0.25,
                nms_threshold: 0.45,
                max_detections: 300,
                device: 'cuda:0',
                half_precision: true,
                num_workers: 8,
                seed: 42
            },
            created_at: new Date('2026-04-12T10:30:00Z')
        },
        {
            id: 'run-2',
            name: 'Fine-tuned domain run',
            evaluation_run_configuration: {
                model: 'yolov8m-ft',
                checkpoint: 'runs/train/exp42/weights/best.pt',
                dataset: 'internal-warehouse-v3',
                dataset_split: 'test',
                image_size: 1280,
                batch_size: 16,
                iou_threshold: 0.75,
                confidence_threshold: 0.4,
                augmentations: ['flip', 'mosaic', 'mixup'],
                classes: ['pallet', 'box', 'person', 'forklift'],
                device: 'cuda:0',
                half_precision: false,
                seed: 7
            },
            created_at: new Date('2026-05-02T14:15:00Z')
        },
        {
            id: 'run-3',
            name: 'Run with no configuration',
            evaluation_run_configuration: {},
            created_at: new Date('2026-05-15T09:00:00Z')
        },
        {
            id: 'run-4',
            name: 'Multi-stage pipeline eval',
            evaluation_run_configuration: {
                model: 'rt-detr-l',
                dataset: 'coco-val-2017',
                dataset_split: 'val',
                image_size: 800,
                metrics: ['mAP@0.5', 'mAP@0.5:0.95', 'precision', 'recall'],
                preprocessing: { normalize: true, resize_mode: 'letterbox', pad_value: 114 },
                postprocessing: { agnostic_nms: false, multi_label: true },
                tta: { enabled: true, scales: [0.83, 1.0, 1.17], flips: ['horizontal'] }
            },
            created_at: new Date('2026-05-17T08:45:00Z')
        }
    ];

    const { Story } = defineMeta({
        title: 'Components/EvaluationRunsPanel',
        component: EvaluationRunsPanel,
        tags: ['autodocs']
    });
</script>

<Story name="With Runs" args={{ evaluationRuns: sampleRuns, onClose: fn() }} />

<Story name="Empty" args={{ evaluationRuns: [], onClose: fn() }} />

<Story name="Loading" args={{ evaluationRuns: [], isLoading: true, onClose: fn() }} />

<Story
    name="Error"
    args={{
        evaluationRuns: [],
        isLoading: false,
        error: 'Failed to fetch evaluation runs',
        onClose: fn()
    }}
/>
