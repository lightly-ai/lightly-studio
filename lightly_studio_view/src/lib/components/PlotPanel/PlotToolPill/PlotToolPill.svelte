<script lang="ts">
    import { untrack, type Component } from 'svelte';
    import { Button } from '$lib/components';
    import { cn } from '$lib/utils';
    import { Hand, Lasso, SquareDashed, type IconProps } from '@lucide/svelte';
    import {
        SELECTION_TOOLS,
        createSelectionToolController,
        type SelectionToolController,
        type ToolMode
    } from './selectionTool';

    interface Props {
        // The element embedding-atlas renders into. Its hidden toolbar is what the pill drives.
        plotContainer: HTMLElement | null;
        // Owned by the parent on purpose: every filter change unmounts the plot while the new
        // embeddings load, and local state would drop the user's tool back to pan each time.
        activeTool: ToolMode;
    }

    let { plotContainer, activeTool = $bindable('pan') }: Props = $props();

    // embedding-atlas has no public setter for its selection mode, so the pill clicks the
    // library's own hidden toolbar buttons. See ./selectionTool.
    const TOOL_ICONS: Record<ToolMode, Component<IconProps>> = {
        pan: Hand,
        rectangle: SquareDashed,
        lasso: Lasso
    };

    // `activeTool` is the user's choice and the pill's source of truth; the controller re-asserts
    // it whenever the library resets to "none" after a selection, keeping the tool sticky.
    let toolController: SelectionToolController | undefined;

    const selectTool = (mode: ToolMode) => {
        activeTool = mode;
        toolController?.reconcile();
    };

    // Read `activeTool` untracked so this effect depends only on `plotContainer`: choosing a tool
    // must not tear the controller (and its pending-click guard) down mid-selection.
    $effect(() => {
        if (plotContainer === null) return;
        toolController = createSelectionToolController(plotContainer, () =>
            untrack(() => activeTool)
        );
        return () => {
            toolController?.destroy();
            toolController = undefined;
        };
    });
</script>

<!-- Placed by PlotPanel's bottom row, which pairs it with the legend. -->
<div
    class="pointer-events-auto flex shrink-0 items-center gap-1 rounded-lg border border-white/10 bg-black/60 p-1 backdrop-blur-sm"
    data-testid="plot-tool-pill"
>
    {#each SELECTION_TOOLS as tool (tool.mode)}
        <Button
            icon={TOOL_ICONS[tool.mode]}
            ariaLabel={tool.label}
            buttonProps={{
                size: 'icon',
                title: tool.label,
                'aria-pressed': activeTool === tool.mode,
                'data-testid': `plot-tool-${tool.mode}`,
                onclick: () => selectTool(tool.mode),
                class: cn(
                    'size-[26px] text-muted-foreground hover:bg-white/10 hover:text-foreground',
                    activeTool === tool.mode && 'bg-white/[0.14] text-foreground'
                )
            }}
        />
    {/each}
</div>
