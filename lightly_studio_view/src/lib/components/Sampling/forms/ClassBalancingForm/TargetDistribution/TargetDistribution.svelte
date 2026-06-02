<script lang="ts">
    import { Trash2 } from '@lucide/svelte';
    import { Button } from '$lib/components/ui/button';
    import { Input } from '$lib/components/ui/input';
    import { Label } from '$lib/components/ui/label';
    import * as Select from '$lib/components/ui/select';
    import FieldTooltip from '$lib/components/FieldTooltip/FieldTooltip.svelte';
    import type { ClassBalancingTargetRow } from '$lib/hooks/useStrategyBuilder';

    interface Props {
        targetDistribution: ClassBalancingTargetRow[];
        annotationLabels: string[];
        onUpdate: (rows: ClassBalancingTargetRow[]) => void;
    }

    let { targetDistribution, annotationLabels, onUpdate }: Props = $props();

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
            type="button"
            variant="outline"
            size="sm"
            onclick={addRow}
            data-testid="class-balancing-add-row"
        >
            Add class
        </Button>
    </div>

    {#if targetDistribution.length === 0}
        <p class="text-sm text-muted-foreground" data-testid="class-balancing-empty-state">
            Add at least one class to balance against.
        </p>
    {/if}

    {#each targetDistribution as row, index (index)}
        <div class="grid grid-cols-[1fr_120px_auto] gap-2">
            <Select.Root
                type="single"
                value={row.class_name}
                onValueChange={(value) => updateRow(index, { class_name: value })}
            >
                <Select.Trigger class="w-full" data-testid={`class-balancing-class-name-${index}`}>
                    {row.class_name || 'Select class'}
                </Select.Trigger>
                <Select.Content>
                    <Select.Group>
                        {#each annotationLabels as label (label)}
                            <Select.Item
                                value={label}
                                {label}
                                data-testid={`class-balancing-class-name-${index}-${label}`}
                            >
                                {label}
                            </Select.Item>
                        {/each}
                    </Select.Group>
                </Select.Content>
            </Select.Root>
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
                data-testid={`class-balancing-weight-${index}`}
            />
            <Button
                type="button"
                variant="ghost"
                size="icon"
                aria-label={`Remove class ${index + 1}`}
                onclick={() => removeRow(index)}
                data-testid={`class-balancing-remove-row-${index}`}
            >
                <Trash2 class="size-4" />
            </Button>
        </div>
    {/each}
</div>
