<script lang="ts">
    import { Box, Move, MousePointer2, RotateCw, Scan } from '@lucide/svelte';
    import { Toolbar, type ToolbarItem } from '$lib/components/ui/toolbar';
    import type { WorkspaceTool } from '../domain';

    interface Props {
        activeTool?: WorkspaceTool;
        onToolChange?: (tool: WorkspaceTool) => void;
    }

    const { activeTool = 'select', onToolChange = () => {} }: Props = $props();

    const items: ToolbarItem[] = [
        { id: 'select', label: 'Select cuboid', icon: MousePointer2 },
        { id: 'create-cuboid', label: 'Create cuboid', icon: Box },
        { id: 'translate', label: 'Move cuboid', icon: Move },
        { id: 'rotate', label: 'Rotate cuboid', icon: RotateCw },
        { id: 'resize', label: 'Resize cuboid', icon: Scan }
    ];
</script>

<div data-testid="workspace-tool-rail">
    <Toolbar {items} {activeTool} onToolChange={(tool) => onToolChange(tool as WorkspaceTool)} />
</div>
