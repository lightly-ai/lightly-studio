<script lang="ts">
    import { Trash2 } from '@lucide/svelte';
    import { Button } from '$lib/components';
    import { Input } from '$lib/components/ui/input';
    import { Label } from '$lib/components/ui/label';
    import { Select, type SelectItem } from '$lib/components/Select';
    import FieldTooltip from '$lib/components/FieldTooltip/FieldTooltip.svelte';
    import type { ClassBalancingTargetRow } from '$lib/hooks/useStrategyBuilder';

    interface Props {
        targetDistribution: ClassBalancingTargetRow[];
        annotationLabels: string[];
        onUpdate: (rows: ClassBalancingTargetRow[]) => void;
        testIdPrefix?: string;
    }

    let {
        targetDistribution,
        annotationLabels,
        onUpdate,
        testIdPrefix = 'class-balancing'
    }: Props = $props();

    function addRow() {
        onUpdate([...targetDistribution, { class_name: '', weight: 0 }]);
    }

    function updateRow(index: number, updates: Partial<ClassBalancingTargetRow>) {
        onUpdate(
            targetDistribution.map((row, rowIndex) =>
                rowIndex === index ? { ...row, ...updates } : row
            )
        );
    }

    function removeRow(index: number) {
        onUpdate(targetDistribution.filter((_, rowIndex) => rowIndex !== index));
    }
</script>

<div class="grid gap-2">
    <div class="flex items-center justify-between">
        <div class="flex items-center gap-1.5">
            <Label>Target Distribution</Label>
            <FieldTooltip
                content="Target proportion for this class (0 to 1). All class proportions must sum to 1. E.g. cat: 0.2, dog: 0.8."
            />
        </div>
        <Button
            variant="outline"
            buttonProps={{
                type: 'button',
                size: 'sm',
                onclick: addRow,
                'data-testid': `${testIdPrefix}-add-row`
            }}
        >
            Add class
        </Button>
    </div>

    {#if targetDistribution.length === 0}
        <p class="text-sm text-muted-foreground" data-testid={`${testIdPrefix}-empty-state`}>
            Add at least one class to balance against.
        </p>
    {/if}

    {#each targetDistribution as row, index (index)}
        {@const rowItems = annotationLabels.map<SelectItem>((label) => ({
            value: label,
            label,
            testId: `${testIdPrefix}-class-name-${index}-${label}`
        }))}
        <div class="grid grid-cols-[1fr_120px_auto] gap-2">
            <Select
                items={rowItems}
                value={row.class_name}
                placeholder="Select class"
                class="w-full"
                testId={`${testIdPrefix}-class-name-${index}`}
                onValueChange={(value) => updateRow(index, { class_name: value })}
            />
            <Input
                type="number"
                min="0"
                max="1"
                step="0.01"
                value={row.weight}
                oninput={(event) =>
                    updateRow(index, {
                        weight: Number((event.currentTarget as HTMLInputElement).value)
                    })}
                class="[appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
                data-testid={`${testIdPrefix}-weight-${index}`}
            />
            <Button
                variant="ghost"
                icon={Trash2}
                ariaLabel={`Remove class ${index + 1}`}
                buttonProps={{
                    type: 'button',
                    size: 'icon',
                    onclick: () => removeRow(index),
                    'data-testid': `${testIdPrefix}-remove-row-${index}`
                }}
            />
        </div>
    {/each}
</div>
