<script lang="ts">
    import ObjectDetectionConfigFields from './ObjectDetectionConfigFields.svelte';

    let {
        iouThreshold = $bindable(0.5),
        classwise = $bindable(true)
    }: {
        iouThreshold?: number;
        classwise?: boolean;
    } = $props();
</script>

<ObjectDetectionConfigFields bind:iouThreshold bind:classwise />

<span data-testid="iou-threshold-state">{iouThreshold.toFixed(2)}</span>
<span data-testid="classwise-state">{String(classwise)}</span>
