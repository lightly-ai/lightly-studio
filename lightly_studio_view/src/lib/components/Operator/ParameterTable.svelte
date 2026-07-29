<script lang="ts">
    import { tick } from 'svelte';
    import { Trash2 } from '@lucide/svelte';
    import { Button } from '$lib/components/ui/button';
    import { Label } from '$lib/components/ui/label';
    import { cn } from '$lib/utils';
    import type { OperatorParameterColumn } from '$lib/hooks/useOperators/useOperators';
    import ParameterTableCell from './ParameterTableCell.svelte';
    import type { ParameterTableRow, ParameterValue } from './parameterTypeConfig';
    import {
        MAX_ROWS_HEIGHT,
        MAX_VISIBLE_ROWS,
        buildBlankRow,
        buildGridStyle,
        isCellInvalid,
        replaceCell
    } from './ParameterTable.helpers';

    interface Props {
        name: string;
        value: ParameterValue;
        required: boolean;
        isMissing: boolean;
        description?: string;
        columns?: OperatorParameterColumn[];
        onUpdate: (value: ParameterValue) => void;
    }

    let { name, value, required, isMissing, description, columns, onUpdate }: Props = $props();

    let rowsContainer = $state<HTMLDivElement | null>(null);

    const cells = $derived(columns ?? []);
    const rows = $derived(Array.isArray(value) ? value : []);
    const isScrollable = $derived(rows.length > MAX_VISIBLE_ROWS);
    const gridStyle = $derived(buildGridStyle(cells.length));

    async function addRow() {
        onUpdate([...rows, buildBlankRow(cells)]);
        // The new row only reaches the DOM after the parent re-renders with the
        // updated value, so wait before scrolling it into view.
        await tick();
        rowsContainer?.scrollTo({ top: rowsContainer.scrollHeight });
    }

    function updateCell(index: number, cell: string, cellValue: ParameterTableRow[string]) {
        onUpdate(replaceCell(rows, index, cell, cellValue));
    }

    function removeRow(index: number) {
        onUpdate(rows.filter((_, rowIndex) => rowIndex !== index));
    }
</script>

<div class="space-y-2">
    <div class="flex items-center justify-between gap-2">
        <Label>
            {name}
            {#if required}
                <span class="text-destructive-text">*</span>
            {/if}
        </Label>
        <Button
            type="button"
            variant="outline"
            size="sm"
            onclick={addRow}
            data-testid={`parameter-table-${name}-add-row`}
        >
            Add row
        </Button>
    </div>

    {#if description}
        <p class="text-sm text-muted-foreground">
            {description}
        </p>
    {/if}

    {#if rows.length === 0}
        <p
            class="text-sm text-muted-foreground"
            data-testid={`parameter-table-${name}-empty-state`}
        >
            No rows yet. Use "Add row" to add one.
        </p>
    {:else}
        <!-- Headers sit outside the scroll container so they stay visible while rows scroll. -->
        <div class="grid gap-2" style={gridStyle}>
            {#each cells as cell (cell.name)}
                <span class="text-xs font-medium text-muted-foreground" title={cell.description}>
                    {cell.name}
                    {#if cell.required}
                        <span class="text-destructive-text">*</span>
                    {/if}
                </span>
            {/each}
            <span></span>
        </div>

        <!-- overflow-y-auto also clips horizontally, cutting off the inputs' focus
             ring, so it is only applied once the rows actually need to scroll. The
             p-2 then keeps that ring clear of the border. -->
        <div
            bind:this={rowsContainer}
            class={cn(
                isScrollable &&
                    `${MAX_ROWS_HEIGHT} overflow-y-auto rounded-md border border-border p-2`
            )}
            data-testid={`parameter-table-${name}-rows`}
        >
            <div class="grid gap-2" style={gridStyle}>
                {#each rows as row, index (index)}
                    {#each cells as cell (cell.name)}
                        <ParameterTableCell
                            column={cell}
                            value={row[cell.name]}
                            isInvalid={isCellInvalid(row, cell, { required, isMissing })}
                            label={`${name} ${cell.name} row ${index + 1}`}
                            testId={`parameter-table-${name}-${cell.name}-${index}`}
                            onUpdate={(cellValue) => updateCell(index, cell.name, cellValue)}
                        />
                    {/each}
                    <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        aria-label={`Remove row ${index + 1}`}
                        onclick={() => removeRow(index)}
                        data-testid={`parameter-table-${name}-remove-row-${index}`}
                    >
                        <Trash2 class="size-4" />
                    </Button>
                {/each}
            </div>
        </div>
    {/if}

    {#if required && isMissing}
        <p class="text-sm text-destructive-text">
            Add at least one row and fill in every required cell.
        </p>
    {/if}
</div>
