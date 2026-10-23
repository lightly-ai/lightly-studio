<script lang="ts">
    import { Box, Hand, Move, MousePointer2, Rotate3d, RotateCw, Scan } from '@lucide/svelte';
    import { Toolbar, type ToolbarItem } from '$lib/components/ui/toolbar';
    import type { WorkspaceTool } from '../domain';

    interface Props {
        activeTool?: WorkspaceTool;
        onToolChange?: (tool: WorkspaceTool) => void;
    }

    const { activeTool = 'select', onToolChange = () => {} }: Props = $props();

    const items: ToolbarItem[] = [
        { id: 'select', label: 'Select', icon: MousePointer2 },
        { id: 'create-cuboid', label: 'Create cuboid', icon: Box },
        { id: 'translate', label: 'Move', icon: Move },
        { id: 'rotate', label: 'Rotate', icon: RotateCw },
        { id: 'resize', label: 'Resize', icon: Scan },
        { id: 'pan', label: 'Pan', icon: Hand, disabledReason: 'Coming soon' },
        { id: 'orbit', label: 'Orbit', icon: Rotate3d, disabledReason: 'Coming soon' }
    ];
</script>

<div data-testid="workspace-tool-rail">
    <Toolbar {items} {activeTool} onToolChange={(tool) => onToolChange(tool as WorkspaceTool)} />
</div>
