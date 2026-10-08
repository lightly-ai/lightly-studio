<script lang="ts">
    import { Label } from '$lib/components/ui/label';
    import { Slider } from '$lib/components/ui/slider';
    import AutoLabelTargets from './AutoLabelTargets.svelte';

    interface Props {
        task: 'object_detection' | 'segmentation';
        prompts: string[];
        overrides: Record<string, string>;
        threshold: number;
    }
    const TASK_OPTIONS = [
        { value: 'object_detection', name: 'Object detection' },
        { value: 'segmentation', name: 'Segmentation' }
    ] as const;

    let {
        task = $bindable(),
        prompts = $bindable(),
        overrides = $bindable(),
        threshold = $bindable()
    }: Props = $props();
</script>

<div class="grid gap-5">
    <fieldset class="grid gap-2">
        <legend class="mb-2 text-sm font-medium">Task</legend>
        <div class="flex flex-wrap gap-4">
            {#each TASK_OPTIONS as option (option.value)}
                <label class="flex items-center gap-2 text-sm">
                    <input
                        type="radio"
                        name="auto-label-task"
                        value={option.value}
                        bind:group={task}
                    />
                    {option.name}
                </label>
            {/each}
        </div>
    </fieldset>
    <AutoLabelTargets bind:prompts bind:overrides />
    <div class="grid gap-3">
        <Label for="auto-label-confidence">Minimum confidence: {threshold.toFixed(2)}</Label>
        <Slider
            id="auto-label-confidence"
            type="single"
            min={0}
            max={1}
            step={0.01}
            bind:value={threshold}
        />
    </div>
</div>
