<script lang="ts">
    import Box from '@lucide/svelte/icons/box';
    import Move from '@lucide/svelte/icons/move';
    import MousePointer2 from '@lucide/svelte/icons/mouse-pointer-2';
    import RotateCw from '@lucide/svelte/icons/rotate-cw';
    import Scan from '@lucide/svelte/icons/scan';
    import { Toolbar, type ToolbarItem } from '$lib/components/ui/toolbar';
    import type { WorkspaceTool } from '../domain';

    interface Props {
        activeTool?: WorkspaceTool;
        onToolChange?: (tool: WorkspaceTool) => void;
    }

    const { activeTool = 'select', onToolChange = () => {} }: Props = $props();

    const items: ToolbarItem[] = [
        { id: 'select', label: 'Select cuboid', icon: MousePointer2 },
        {
            id: 'create-cuboid',
            label: 'Create cuboid',
            icon: Box,
            shortcut: 'c',
            action: 'create'
        },
        { id: 'translate', label: 'Move cuboid', icon: Move },
        { id: 'rotate', label: 'Rotate cuboid', icon: RotateCw },
        { id: 'resize', label: 'Resize cuboid', icon: Scan }
    ];
</script>

<div data-testid="workspace-tool-rail">
    <Toolbar {items} {activeTool} onToolChange={(tool) => onToolChange(tool as WorkspaceTool)} />
</div>
