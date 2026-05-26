<script lang="ts">
    import { Label } from '$lib/components/ui/label';
    import * as Select from '$lib/components/ui/select';
    import type { AnnotationCollectionView } from '$lib/api/lightly_studio_local/types.gen';
    import {
        BALANCING_MODE_LABELS,
        type BalancingMode
    } from '$lib/components/Sampling/balancingMode';

    interface Props {
        balancingMode: BalancingMode;
        annotationCollections: AnnotationCollectionView[];
        annotationSourceId: string;
        onBalancingModeChange: (mode: BalancingMode) => void;
        onAnnotationSourceChange: (annotationSourceId: string) => void;
    }

    let {
        balancingMode,
        annotationCollections,
        annotationSourceId,
        onBalancingModeChange,
        onAnnotationSourceChange
    }: Props = $props();

    const selectedAnnotationSourceName = $derived(
        annotationSourceId === ''
            ? 'All annotation sources'
            : (annotationCollections.find((source) => source.collection_id === annotationSourceId)
                  ?.name ?? 'Select annotation source')
    );
</script>

<div class="grid grid-cols-4 items-center gap-4">
    <Label for="balancing-mode" class="text-right text-foreground">Balancing Mode</Label>
    <Select.Root
        type="single"
        name="balancing-mode"
        value={balancingMode}
        onValueChange={(v) => onBalancingModeChange(v as BalancingMode)}
    >
        <Select.Trigger
            id="balancing-mode"
            class="col-span-3"
            data-testid="sampling-dialog-balancing-mode-select"
        >
            {BALANCING_MODE_LABELS[balancingMode]}
        </Select.Trigger>
        <Select.Content>
            <Select.Group>
                <Select.Item
                    value="uniform"
                    label="Uniform"
                    data-testid="sampling-balancing-mode-uniform">Uniform</Select.Item
                >
                <Select.Item value="dictionary" label="Dictionary" disabled
                    >Dictionary (Coming soon)</Select.Item
                >
                <Select.Item
                    value="input"
                    label="Input"
                    data-testid="sampling-balancing-mode-input"
                    disabled>Input (Coming soon)</Select.Item
                >
            </Select.Group>
        </Select.Content>
    </Select.Root>
</div>

<div class="grid grid-cols-4 items-center gap-4">
    <Label for="annotation-source" class="text-right text-foreground">Annotation Source</Label>
    <Select.Root
        type="single"
        name="annotation-source"
        value={annotationSourceId}
        allowDeselect
        onValueChange={onAnnotationSourceChange}
    >
        <Select.Trigger
            id="annotation-source"
            class="col-span-3"
            data-testid="sampling-dialog-annotation-source-select"
        >
            {selectedAnnotationSourceName}
        </Select.Trigger>
        <Select.Content>
            <Select.Group>
                {#if annotationCollections.length === 0}
                    <div
                        class="py-1.5 pl-8 pr-2 text-sm italic text-muted-foreground"
                        data-testid="sampling-dialog-no-annotation-sources"
                    >
                        No annotation sources available.
                    </div>
                {:else}
                    {#each annotationCollections as source (source.collection_id)}
                        <Select.Item
                            value={source.collection_id}
                            label={source.name}
                            data-testid={`sampling-annotation-source-${source.collection_id}`}
                        >
                            {source.name}
                        </Select.Item>
                    {/each}
                {/if}
            </Select.Group>
        </Select.Content>
    </Select.Root>
</div>
