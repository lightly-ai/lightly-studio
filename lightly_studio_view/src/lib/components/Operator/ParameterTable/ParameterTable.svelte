<script lang="ts">
    import { tick } from 'svelte';
    import { Trash2 } from '@lucide/svelte';
    import { Button } from '$lib/components/ui/button';
    import { Label } from '$lib/components/ui/label';
    import { cn } from '$lib/utils';
    import type { OperatorParameterColumn } from '$lib/hooks';
    import ParameterTableCell from './ParameterTableCell/ParameterTableCell.svelte';
    import type { ParameterTableRow, ParameterValue } from '../parameterTypeConfig';
    import {
        MAX_TABLE_HEIGHT,
        buildBlankRow,
        buildGridStyle,
        isCellInvalid,
        replaceCell
    } from './ParameterTable.helpers';

    interface Props {
        /** Name of the table parameter, shown as its label and used to build test ids. */
        name: string;
        /** Current parameter value. Anything other than an array of rows renders as an empty table. */
        value: ParameterValue;
        /** Whether the parameter has to be filled in before the operator can run. */
        required: boolean;
        /** Whether the parameter is currently blocking submission, which reveals the error message. */
        isMissing: boolean;
        /** Optional help text shown under the label. */
        description?: string;
        /** The columns every row is made of. Omitted or empty renders the table without data columns. */
        columns?: OperatorParameterColumn[];
        /** Called with the full row list whenever a row is added, edited or removed. */
        onUpdate: (value: ParameterValue) => void;
    }

    let { name, value, required, isMissing, description, columns, onUpdate }: Props = $props();

    let tableContainer = $state<HTMLDivElement | null>(null);

    const cells = $derived(columns ?? []);
    const rows = $derived(Array.isArray(value) ? value : []);
    const gridStyle = $derived(buildGridStyle(cells.length));

    async function addRow() {
        onUpdate([...rows, buildBlankRow(cells)]);
        // The new row only reaches the DOM after the parent re-renders with the
        // updated value, so wait before scrolling it into view.
        await tick();
        tableContainer?.scrollTo({ top: tableContainer.scrollHeight });
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
        <!-- One box scrolls both ways, so the header has to live inside it: a column-scrolling table
             cannot keep the header out of the scroll container and still scroll it horizontally in
             sync. Being a direct child of that container is also what lets the header stick — its
             containing block is the container's whole content box, unlike the earlier sticky header
             cells, whose own grid row track scrolled out from under them. The p-2 keeps the inputs'
             focus ring clear of the clipping edge, which now cuts horizontally as well as vertically,
             and scroll-padding-top keeps a tabbed-to cell from landing under the header.

             min-w-0 is what keeps the scrolling inside this box. The grids below have a definite
             minimum width per column, so their min-content width grows with the column count, and a
             flex or grid ancestor would otherwise be forced to that width rather than letting the box
             shrink and scroll — widening the whole dialog instead. -->
        <div
            bind:this={tableContainer}
            class={cn(
                MAX_TABLE_HEIGHT,
                'min-w-0 overflow-auto rounded-md border border-border p-2 [scroll-padding-top:1.5rem]'
            )}
            data-testid={`parameter-table-${name}-rows`}
        >
            <!-- The remove button column sticks the other way round, and for the mirror reason: a grid
                 row track spans the full width of the grid, so a right inset pins the button for the
                 whole horizontal scroll range. Its opaque background is what hides the cells passing
                 underneath, and it has to cover the gutter on one side and the container's padding on
                 the other, which take different mechanisms:

                 -mr-2 covers the gutter to the left. A negative margin makes the stretched grid item
                 resolve 0.5rem wider than its track, and that surplus hangs off the left edge, over the
                 gap between this track and the last data column. pl-2 then gives a cell somewhere to
                 disappear into behind the border-l instead of being cut off flush against the icon.

                 right-[-0.5rem] covers the container's p-2 to the right, and a plain right-0 does not:
                 sticky insets resolve against the scrollport, which is the padding box, but a sticky box
                 is only ever shifted *inward* — and this one's flow position already sits at the content
                 box edge, 0.5rem inside that rect, so right-0 is satisfied without moving it and leaves
                 the padding exposed. Since the padding scrolls with the content and the container paints
                 its background beneath its descendants, cells would show through that strip. The
                 negative inset lets the box rest 0.5rem further out, flush against the border. -->
            <!-- The header covers the container's top padding the same way the remove column covers its
                 right padding, and for the same reason: top-0 alone would be satisfied without moving
                 the header, because its flow position already sits at the content box edge, inside the
                 scrollport. Rows would then scroll visibly through that strip.

                 The pairing differs from the remove column's, though. Growing the box is what is wanted
                 here, not translating it: -mt-2 pulls the top edge up into the padding so the background
                 covers it, and pt-2 puts the inner spacing back so the labels stay exactly where they
                 were. Using top-[-0.5rem] on its own would translate the whole header instead, sliding
                 the labels up against the border over the first half rem of scroll — and only while
                 scrolling, so it looks correct at rest. -->
            <div
                class="sticky top-[-0.5rem] z-20 -mt-2 grid gap-2 bg-background pt-2"
                style={gridStyle}
            >
                {#each cells as cell (cell.name)}
                    <span
                        class="text-xs font-medium text-muted-foreground"
                        title={cell.description}
                    >
                        {cell.name}
                        {#if cell.required}
                            <span class="text-destructive-text">*</span>
                        {/if}
                    </span>
                {/each}
                <!-- z-10 to paint over the labels scrolling underneath. Sticky would already do that
                     as a positioned box, but the rows' cell says so outright and this matches it. -->
                <span
                    class="sticky right-[-0.5rem] z-10 -mr-2 border-l border-border bg-background pl-2 pr-2"
                ></span>
            </div>

            <div class="mt-2 grid gap-2" style={gridStyle}>
                {#each rows as row, index (index)}
                    {#each cells as cell (cell.name)}
                        <ParameterTableCell
                            column={cell}
                            value={row[cell.name]}
                            isInvalid={isCellInvalid(row, cell, { isMissing })}
                            label={`${name} ${cell.name} row ${index + 1}`}
                            testId={`parameter-table-${name}-${cell.name}-${index}`}
                            onUpdate={(cellValue) => updateCell(index, cell.name, cellValue)}
                        />
                    {/each}
                    <!-- The button keeps its own hover background, so the opaque backdrop the sticky
                         column needs goes on a wrapper instead of on the button itself. -->
                    <div
                        class="sticky right-[-0.5rem] z-10 -mr-2 border-l border-border bg-background pl-2 pr-2"
                    >
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
                    </div>
                {/each}
            </div>
        </div>
    {/if}

    <!-- An optional table only blocks once it holds a row, so asking for one would be wrong there. -->
    {#if isMissing}
        <p class="text-sm text-destructive-text">
            {required && rows.length === 0
                ? 'Add at least one row and fill in every required cell.'
                : 'Fill in every required cell.'}
        </p>
    {/if}
</div>
