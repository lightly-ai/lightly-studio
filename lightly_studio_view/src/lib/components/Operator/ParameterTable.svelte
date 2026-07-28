<script lang="ts">
    import { tick } from 'svelte';
    import { Trash2 } from '@lucide/svelte';
    import { Button } from '$lib/components/ui/button';
    import { Input } from '$lib/components/ui/input';
    import { Label } from '$lib/components/ui/label';
    import { cn } from '$lib/utils';
    import type { ParameterTableRow, ParameterValue } from './parameterTypeConfig';

    const MAX_VISIBLE_ROWS = 4;
    // Inputs are h-10 (2.5rem) and rows are gap-2 (0.5rem) apart, so four rows
    // measure 4 * 2.5rem + 3 * 0.5rem. Beyond that the rows area scrolls itself
    // instead of pushing the dialog footer out of view.
    const MAX_ROWS_HEIGHT = 'max-h-[11.5rem]';

    interface Props {
        name: string;
        value: ParameterValue;
        required: boolean;
        isMissing: boolean;
        description?: string;
        columns?: string[];
        onUpdate: (value: ParameterValue) => void;
    }

    let { name, value, required, isMissing, description, columns, onUpdate }: Props = $props();

    let rowsContainer = $state<HTMLDivElement | null>(null);

    const cells = $derived(columns ?? []);
    const rows = $derived(Array.isArray(value) ? value : []);
    const isScrollable = $derived(rows.length > MAX_VISIBLE_ROWS);
    // Tailwind cannot compile a class built at runtime, so the column count goes through style.
    const gridStyle = $derived(
        `grid-template-columns: repeat(${cells.length}, minmax(0, 1fr)) auto`
    );

    async function addRow() {
        const blankRow: ParameterTableRow = Object.fromEntries(cells.map((cell) => [cell, '']));
        onUpdate([...rows, blankRow]);
        // The new row only reaches the DOM after the parent re-renders with the
        // updated value, so wait before scrolling it into view.
        await tick();
        rowsContainer?.scrollTo({ top: rowsContainer.scrollHeight });
    }

    function updateCell(index: number, cell: string, cellValue: string) {
        onUpdate(
            rows.map((row, rowIndex) => (rowIndex === index ? { ...row, [cell]: cellValue } : row))
        );
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
            {#each cells as cell (cell)}
                <span class="text-xs font-medium text-muted-foreground">{cell}</span>
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
                    {#each cells as cell (cell)}
                        <Input
                            type="text"
                            value={row[cell] ?? ''}
                            aria-label={`${name} ${cell} row ${index + 1}`}
                            aria-invalid={required && isMissing}
                            oninput={(event: Event) =>
                                updateCell(
                                    index,
                                    cell,
                                    (event.currentTarget as HTMLInputElement).value
                                )}
                            data-testid={`parameter-table-${name}-${cell}-${index}`}
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
        <p class="text-sm text-destructive-text">Add at least one row and fill in every cell.</p>
    {/if}
</div>
