<script module lang="ts">
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import { makeClassMetrics, makeComparedRun } from '../fixtures';
    import EvaluationComparisonView from './EvaluationComparisonView.svelte';

    const largeModel = makeComparedRun('yolo26-l', {
        mean_average_precision: 0.512,
        mean_average_precision_by_iou_threshold: { '0.5': 0.701, '0.75': 0.553 },
        precision: 0.71,
        recall: 0.64,
        f1: 0.67,
        per_class: [
            makeClassMetrics('car', 0.62),
            makeClassMetrics('person', 0.55),
            makeClassMetrics('bicycle', 0.36)
        ]
    });
    const mediumModel = makeComparedRun('yolo26-m', {
        mean_average_precision: 0.478,
        mean_average_precision_by_iou_threshold: { '0.5': 0.672, '0.75': 0.514 },
        precision: 0.69,
        recall: 0.6,
        f1: 0.64,
        per_class: [
            makeClassMetrics('car', 0.58),
            makeClassMetrics('person', 0.57),
            makeClassMetrics('bicycle', 0.28)
        ]
    });
    const withoutAveragePrecision = makeComparedRun(
        'yolo26-s',
        { mean_average_precision: null, mean_average_precision_by_iou_threshold: null },
        { stale_since: new Date('2026-11-20T00:00:00Z') }
    );

    const MANY_CLASS_COUNT = 40;
    const manyClassLabels = Array.from(
        { length: MANY_CLASS_COUNT },
        (_, index) => `class-${String(index + 1).padStart(2, '0')}`
    );
    const manyClassesModel = (id: string, seed: number) =>
        makeComparedRun(id, {
            per_class: manyClassLabels.map((label, index) =>
                makeClassMetrics(label, ((index * seed) % 97) / 100)
            )
        });

    const { Story } = defineMeta({
        title: 'Evaluation/EvaluationComparisonView',
        component: EvaluationComparisonView
    });
</script>

<Story
    name="Object detection"
    args={{ taskType: 'object_detection', runs: [mediumModel, largeModel] }}
/>

<Story
    name="With warnings"
    args={{
        taskType: 'object_detection',
        runs: [
            largeModel,
            {
                ...withoutAveragePrecision,
                run: { ...withoutAveragePrecision.run, gt_annotation_source: 'ground_truth_v2' }
            }
        ]
    }}
/>

<Story
    name="Many annotation classes"
    args={{
        taskType: 'object_detection',
        runs: [manyClassesModel('yolo26-l', 37), manyClassesModel('yolo26-m', 53)]
    }}
/>
