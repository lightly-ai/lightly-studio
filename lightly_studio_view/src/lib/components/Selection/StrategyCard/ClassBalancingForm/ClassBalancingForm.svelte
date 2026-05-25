<script lang="ts">
    import { Trash2 } from '@lucide/svelte';
    import { Button } from '$lib/components/ui/button';
    import { Input } from '$lib/components/ui/input';
    import { Label } from '$lib/components/ui/label';
    import * as Select from '$lib/components/ui/select';
    import type {
        ClassBalancingTargetRow,
        ClassBalancingParams,
        StrategyParams
    } from '../../useStrategyBuilder/useStrategyBuilder';

    interface Props {
        params: ClassBalancingParams;
        annotationLabels: string[];
        onUpdate: (params: Partial<StrategyParams>) => void;
    }

    let { params, annotationLabels, onUpdate }: Props = $props();

    function updateRows(rows: ClassBalancingTargetRow[]) {
        onUpdate({ target_distribution: rows });
    }

    function addRow() {
        updateRows([...params.target_distribution, { class_name: '', weight: 1 }]);
    }

    function updateRow(index: number, updates: Partial<ClassBalancingTargetRow>) {
        updateRows(
            params.target_distribution.map((row, rowIndex) =>
                rowIndex === index ? { ...row, ...updates } : row
            )
        );
    }

    function removeRow(index: number) {
        updateRows(params.target_distribution.filter((_, rowIndex) => rowIndex !== index));
    }
</script>

<div class="grid gap-3" data-testid="class-balancing-form">
    <div class="grid gap-2">
        <Label for="class-balancing-strength">Strength</Label>
        <Input
            id="class-balancing-strength"
            type="number"
            min="0"
            step="0.1"
            value={params.strength}
            oninput={(event) =>
                onUpdate({ strength: Number((event.currentTarget as HTMLInputElement).value) })}
            data-testid="strategy-class-balancing-strength-input"
        />
    </div>

    <div class="grid gap-2">
        <div class="flex items-center justify-between">
            <Label>Target Distribution</Label>
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

        {#if params.target_distribution.length === 0}
            <p class="text-sm text-muted-foreground" data-testid="class-balancing-empty-state">
                Add at least one class to balance against.
            </p>
        {/if}

        {#each params.target_distribution as row, index (index)}
            <div class="grid grid-cols-[1fr_120px_auto] gap-2">
                <Select.Root
                    type="single"
                    value={row.class_name}
                    onValueChange={(value) => updateRow(index, { class_name: value })}
                >
                    <Select.Trigger
                        class="w-full"
                        data-testid={`class-balancing-class-name-${index}`}
                    >
                        {row.class_name || 'Select class'}
                    </Select.Trigger>
                    <Select.Content>
                        <Select.Group>
                            {#each annotationLabels as label (label)}
                                <Select.Item
                                    value={label}
                                    label={label}
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
                    step="0.1"
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
</div>
