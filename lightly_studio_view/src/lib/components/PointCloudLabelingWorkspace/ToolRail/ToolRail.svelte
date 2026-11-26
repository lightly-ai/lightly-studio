<script lang="ts">
    import Box from '@lucide/svelte/icons/box';
    import MousePointer2 from '@lucide/svelte/icons/mouse-pointer-2';
    import { Toolbar, type ToolbarItem } from '$lib/components/ui/toolbar';
    import { useSettings } from '$lib/hooks/useSettings';
    import type { WorkspaceTool } from '../domain';
    import { isSceneNavigationKey } from '../SceneViewport/sceneNavigationInput';

    interface Props {
        activeTool?: WorkspaceTool;
        onToolChange?: (tool: WorkspaceTool) => void;
    }

    const { activeTool = 'select', onToolChange = () => {} }: Props = $props();

    const { settingsStore } = useSettings();

    const items: ToolbarItem[] = $derived([
        {
            id: 'select',
            label: 'Select cuboid',
            icon: MousePointer2,
            shortcut: $settingsStore.key_point_cloud_select,
            action: 'select'
        },
        {
            id: 'create-cuboid',
            label: 'Create cuboid',
            icon: Box,
            shortcut: $settingsStore.key_point_cloud_create_cuboid,
            action: 'create'
        }
    ]);

    // W/A/S/D move the camera, so a tool shortcut recorded on one of them never fires.
    const isToolShortcut = (event: KeyboardEvent) => !isSceneNavigationKey(event.key);
</script>

<div data-testid="workspace-tool-rail">
    <Toolbar
        {items}
        {activeTool}
        onToolChange={(tool) => onToolChange(tool as WorkspaceTool)}
        shouldHandleShortcut={isToolShortcut}
    />
</div>
