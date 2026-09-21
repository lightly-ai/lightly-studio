<script lang="ts">
    import { Label } from '$lib/components/ui/label';
    import { Slider } from '$lib/components/ui/slider';
    import { Button } from '$lib/components/ui/button';
    import AutoLabelTargets from './AutoLabelTargets.svelte';
    import { supportsTask } from './AutoLabelDialog.helpers';
    import { autoLabelError, type useAutoLabelRun } from './useAutoLabelRun.svelte';
    interface Props {
        description: ReturnType<typeof useAutoLabelRun>['description'];
        task: '' | 'object_detection' | 'segmentation';
        prompts: string[];
        overrides: Record<string, string>;
        threshold: number;
    }
    const TASK_OPTIONS = [
        { value: 'object_detection', name: 'Object detection' },
        { value: 'segmentation', name: 'Segmentation' }
    ] as const;

    let {
        description,
        task = $bindable(),
        prompts = $bindable(),
        overrides = $bindable(),
        threshold = $bindable()
    }: Props = $props();
</script>

<div class="grid gap-5">
    <div class="grid gap-1 text-sm">
        {#if description.isPending}
            <p role="status">Checking model connection...</p>
        {:else if description.isError}
            <p role="alert" class="text-destructive-text">{autoLabelError(description.error)}</p>
        {:else if description.data}
            <p class="break-words font-medium">{description.data.model_key}</p>
            <p class="break-all text-xs text-muted-foreground">{description.data.endpoint}</p>
            <p role="status">{description.data.ready ? 'Ready' : 'Model is loading'}</p>
            {#if !description.data.supported_conditioning.includes('targets')}
                <p class="text-destructive-text">This model does not support target prompts.</p>
            {/if}
        {/if}
        <Button
            type="button"
            variant="outline"
            class="mt-1 w-fit"
            disabled={description.isFetching}
            onclick={() => description.refetch()}>Check connection</Button
        >
    </div>
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
                        disabled={!supportsTask({
                            capabilities: description.data?.capabilities,
                            task: option.value
                        })}
                    />
                    {option.name}
                </label>
            {/each}
        </div>
    </fieldset>
    <AutoLabelTargets classes={description.data?.classes} bind:prompts bind:overrides />
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
