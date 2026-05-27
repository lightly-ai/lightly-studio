<script lang="ts">
    import { ChevronDown, Trash2 } from '@lucide/svelte';
    import { Button } from '$lib/components/ui/button';
    import { Input } from '$lib/components/ui/input';
    import { Label } from '$lib/components/ui/label';
    import * as Popover from '$lib/components/ui/popover';
    import * as Select from '$lib/components/ui/select';
    import FieldTooltip from '../../FieldTooltip.svelte';
    import type {
        ClassBalancingAnnotationSource,
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

    const ANNOTATION_SOURCE_OPTIONS: {
        value: ClassBalancingAnnotationSource;
        label: string;
        tooltip: string;
    }[] = [
        {
            value: 'uniform',
            label: 'Uniform',
            tooltip: 'Equal share for every class present in the dataset.'
        },
        {
            value: 'input',
            label: 'Input',
            tooltip: 'Mirrors the class distribution of the candidate input set.'
        },
        {
            value: 'dictionary',
            label: 'Dictionary',
            tooltip: 'Define a specific target distribution (e.g. 20% cat, 80% dog).'
        }
    ];

    let annotationSourceOpen = $state(false);
    let hoveredAnnotationSource = $state<ClassBalancingAnnotationSource | null>(null);

    let selectedAnnotationSourceLabel = $derived(
        ANNOTATION_SOURCE_OPTIONS.find((o) => o.value === params.annotation_source)!.label
    );

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
        <div class="flex items-center gap-1.5">
            <Label>Annotation source</Label>
            <FieldTooltip
                content="Where class labels come from. Choose how the target distribution is defined."
            />
        </div>
        <Popover.Root bind:open={annotationSourceOpen}>
            <Popover.Trigger class="w-full">
                <button
                    type="button"
                    class="flex h-9 w-full items-center justify-between rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm ring-offset-background focus:outline-none focus:ring-1 focus:ring-ring"
                    data-testid="class-balancing-annotation-source"
                >
                    {selectedAnnotationSourceLabel}
                    <ChevronDown class="size-4 opacity-50" />
                </button>
            </Popover.Trigger>
            <Popover.Content class="w-40 p-1" align="start">
                <div class="flex flex-col gap-1">
                    {#each ANNOTATION_SOURCE_OPTIONS as option (option.value)}
                        <div
                            class="relative"
                            onmouseenter={() => (hoveredAnnotationSource = option.value)}
                            onmouseleave={() => (hoveredAnnotationSource = null)}
                        >
                            <button
                                type="button"
                                class="w-full rounded-sm px-2 py-1.5 text-left text-sm hover:bg-accent hover:text-accent-foreground"
                                onclick={() => {
                                    onUpdate({
                                        annotation_source: option.value
                                    });
                                    annotationSourceOpen = false;
                                }}
                                data-testid={`class-balancing-annotation-source-${option.value}`}
                            >
                                {option.label}
                            </button>
                            {#if hoveredAnnotationSource === option.value}
                                <div
                                    class="absolute left-full top-1/2 z-[9999] ml-2 w-max max-w-[200px] -translate-y-1/2 rounded-md bg-popover px-3 py-1.5 text-xs text-popover-foreground shadow-md"
                                    role="tooltip"
                                >
                                    {option.tooltip}
                                </div>
                            {/if}
                        </div>
                    {/each}
                </div>
            </Popover.Content>
        </Popover.Root>
    </div>

    <div class="grid gap-2">
        <div class="flex items-center gap-1.5">
            <Label for="class-balancing-strength">Strength</Label>
            <FieldTooltip content="Relative weight of this strategy in the combination. A strength of 2 gives this strategy twice the influence of one with strength 1. Must be a positive number." />
        </div>
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

    {#if params.annotation_source === 'dictionary'}
    <div class="grid gap-2">
        <div class="flex items-center justify-between">
            <div class="flex items-center gap-1.5">
                <Label>Target Distribution</Label>
                <FieldTooltip content="Relative proportion of this class in the selected output. A class with weight 2 is selected twice as often as one with weight 1." />
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
    {/if}
</div>
