<script lang="ts">
    import * as Select from '$lib/components/ui/select';
    import type { AnnotationLabelTable } from '$lib/api/lightly_studio_local/types.gen';
    import ClassTargetRow from './ClassTargetRow.svelte';

    interface Props {
        annotationLabels: AnnotationLabelTable[];
        classTargets: Record<string, number>;
        onClassTargetsChange: (targets: Record<string, number>) => void;
    }

    let { annotationLabels, classTargets, onClassTargetsChange }: Props = $props();

    const targetEntries = $derived(Object.entries(classTargets));
    const unusedLabels = $derived(
        annotationLabels.filter((label) => !(label.annotation_label_name in classTargets))
    );

    function addClassTarget(labelName: string | undefined) {
        if (!labelName || labelName in classTargets) return;
        onClassTargetsChange({ ...classTargets, [labelName]: 1 });
    }

    function removeClassTarget(labelName: string) {
        const nextTargets = { ...classTargets };
        delete nextTargets[labelName];
        onClassTargetsChange(nextTargets);
    }

    function updateClassTarget(labelName: string, target: number) {
        const targetValue = Number.isFinite(target) ? Math.max(target, 0) : 0;
        onClassTargetsChange({ ...classTargets, [labelName]: targetValue });
    }
</script>

<div class="col-span-3 grid gap-2" data-testid="sampling-class-targets-editor">
    {#if targetEntries.length > 0}
        <div class="grid gap-2">
            {#each targetEntries as [labelName, target] (labelName)}
                <ClassTargetRow
                    {labelName}
                    {target}
                    onTargetChange={updateClassTarget}
                    onRemove={removeClassTarget}
                />
            {/each}
        </div>
    {/if}

    <Select.Root
        type="single"
        name="class-target"
        value=""
        disabled={unusedLabels.length === 0}
        onValueChange={addClassTarget}
    >
        <Select.Trigger id="class-target" data-testid="sampling-class-target-add-select">
            {annotationLabels.length === 0
                ? 'No classes available'
                : unusedLabels.length === 0
                  ? 'All classes added'
                  : 'Add class'}
        </Select.Trigger>
        <Select.Content>
            <Select.Group>
                {#if annotationLabels.length === 0}
                    <div
                        class="py-1.5 pl-8 pr-2 text-sm italic text-muted-foreground"
                        data-testid="sampling-class-target-no-labels"
                    >
                        No annotation classes available.
                    </div>
                {:else}
                    {#each unusedLabels as label (label.annotation_label_name)}
                        <Select.Item
                            value={label.annotation_label_name}
                            label={label.annotation_label_name}
                            data-testid={`sampling-class-target-option-${label.annotation_label_name}`}
                        >
                            {label.annotation_label_name}
                        </Select.Item>
                    {/each}
                {/if}
            </Select.Group>
        </Select.Content>
    </Select.Root>
</div>
