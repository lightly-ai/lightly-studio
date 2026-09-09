<script lang="ts">
    import type { Component } from 'svelte';
    import type { IconProps } from '@lucide/svelte';
    import { Box, Hand, Move, MousePointer2, Rotate3d, RotateCw, Scan } from '@lucide/svelte';
    import { Button } from '$lib/components';
    import type { WorkspaceTool } from '../domain';

    /** Placeholder tool rail; tool activation lands with the interaction state machine. */
    const { activeTool = 'select' }: { activeTool?: WorkspaceTool } = $props();

    const tools: { tool: WorkspaceTool; label: string; icon: Component<IconProps> }[] = [
        { tool: 'select', label: 'Select', icon: MousePointer2 },
        { tool: 'create-cuboid', label: 'Create cuboid', icon: Box },
        { tool: 'translate', label: 'Move', icon: Move },
        { tool: 'rotate', label: 'Rotate', icon: RotateCw },
        { tool: 'resize', label: 'Resize', icon: Scan },
        { tool: 'pan', label: 'Pan', icon: Hand },
        { tool: 'orbit', label: 'Orbit', icon: Rotate3d }
    ];
</script>

<div class="pointer-events-none absolute left-1 top-1 z-20">
    <nav
        class="pointer-events-auto flex select-none flex-col items-stretch gap-1 rounded-lg bg-muted p-1 shadow-md"
        data-testid="workspace-tool-rail"
        aria-label="Labeling tools"
    >
        {#each tools as { tool, label, icon } (tool)}
            <Button
                variant={tool === activeTool ? 'secondary' : 'ghost'}
                {icon}
                ariaLabel={label}
                buttonProps={{
                    disabled: true,
                    size: 'sm',
                    class: 'h-8 w-8 p-0',
                    title: `${label} (coming soon)`
                }}
            />
        {/each}
    </nav>
</div>
