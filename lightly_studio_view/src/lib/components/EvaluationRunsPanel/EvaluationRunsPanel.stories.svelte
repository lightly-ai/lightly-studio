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
                iou_threshold: 0.5,
                confidence_threshold: 0.25,
                dataset_split: 'val'
            },
            created_at: new Date('2026-04-12T10:30:00Z')
        },
        {
            id: 'run-2',
            name: 'Fine-tuned domain run',
            evaluation_run_configuration: {
                model: 'yolov8m-ft',
                iou_threshold: 0.75,
                augmentations: ['flip', 'mosaic']
            },
            created_at: new Date('2026-05-02T14:15:00Z')
        },
        {
            id: 'run-3',
            name: 'Run with no configuration',
            evaluation_run_configuration: {},
            created_at: new Date('2026-05-15T09:00:00Z')
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
