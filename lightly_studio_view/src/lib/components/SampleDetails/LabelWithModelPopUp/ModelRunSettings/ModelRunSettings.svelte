<script lang="ts">
    import Box from '@lucide/svelte/icons/box';
    import SquareDashed from '@lucide/svelte/icons/square-dashed';
    import type { LabelingModelView } from '$lib/api/lightly_studio_local';
    import { Select } from '$lib/components/Select';
    import ThresholdInput from '../ThresholdInput/ThresholdInput.svelte';

    interface Props {
        models: LabelingModelView[];
        model: LabelingModelView | null;
        threshold: number;
        onThresholdChange: (value: number) => void;
        onModelChange: (value: string) => void;
        disabled: boolean;
    }
    let { models, model, threshold, onThresholdChange, onModelChange, disabled }: Props = $props();
    const TASKS = {
        object_detection: { group: 'Object detection', icon: Box },
        instance_segmentation: { group: 'Instance segmentation', icon: SquareDashed }
    } as const;
    const items = $derived(
        models.map((item) => ({ value: item.id, label: item.id, ...TASKS[item.task] }))
    );
</script>

<fieldset {disabled} class="grid min-w-0 gap-1.5">
    <Select
        {items}
        {disabled}
        selectProps={{ 'aria-label': 'Model' }}
        value={model?.id}
        size="sm"
        placeholder="Select a model"
        testId="label-with-model-select"
        onValueChange={onModelChange}
    />
    {#if model}<p class="text-xs text-muted-foreground">{TASKS[model.task].group}</p>{/if}
    <ThresholdInput value={threshold} onChange={onThresholdChange} {disabled} />
</fieldset>
