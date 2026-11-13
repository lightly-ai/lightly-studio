<script lang="ts">
    import Box from '@lucide/svelte/icons/box';
    import Hand from '@lucide/svelte/icons/hand';
    import Move from '@lucide/svelte/icons/move';
    import MousePointer2 from '@lucide/svelte/icons/mouse-pointer-2';
    import Rotate3d from '@lucide/svelte/icons/rotate-3d';
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
