<script lang="ts">
    import type { Component } from 'svelte';
    import type { IconProps } from '@lucide/svelte';
    import { Box, Hand, Move, MousePointer2, Rotate3d, RotateCw, Scan } from '@lucide/svelte';
    import { Button } from '$lib/components';
    import type { WorkspaceTool } from '../domain';

    interface Props {
        activeTool?: WorkspaceTool;
        onToolChange?: (tool: WorkspaceTool) => void;
    }

    const { activeTool = 'select', onToolChange }: Props = $props();

    const ENABLED_TOOLS = new Set<WorkspaceTool>([
        'select',
        'create-cuboid',
        'translate',
        'rotate',
        'resize'
    ]);

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

<div class="pointer-events-none absolute left-0 top-0 z-20 ml-5 mt-4">
    <nav
        class="pointer-events-auto flex select-none flex-col items-stretch gap-1 rounded-lg bg-muted p-1 shadow-md"
        data-testid="workspace-tool-rail"
        aria-label="Labeling tools"
    >
        {#each tools as { tool, label, icon } (tool)}
            {@const enabled = ENABLED_TOOLS.has(tool)}
            <Button
                variant={tool === activeTool ? 'secondary' : 'ghost'}
                {icon}
                ariaLabel={label}
                buttonProps={{
                    disabled: !enabled,
                    size: 'sm',
                    class: 'h-8 w-8 p-0',
                    title: enabled ? label : `${label} (coming soon)`,
                    onclick: enabled ? () => onToolChange?.(tool) : undefined
                }}
            />
        {/each}
    </nav>
</div>
