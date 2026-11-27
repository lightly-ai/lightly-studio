/**
 * Configuration for the shortcut settings rows displayed in SettingsDialog.
 *
 * Each entry maps a unique HTML id and user-visible label to a key in the
 * SettingsDialogShortcutState managed by settingsDialogState.ts.
 */

/** Keys of the shortcut state object that can be recorded by the user. */
export type ShortcutSettingKey =
    | 'hideAnnotations'
    | 'toggleEditMode'
    | 'keyToolbarSelection'
    | 'keyToolbarDrag'
    | 'keyToolbarBoundingBox'
    | 'keyToolbarSegmentationMask'
    | 'keyToolbarSlic'
    | 'keyToolbarBrush'
    | 'keyToolbarEraser'
    | 'keyPreviousCamera'
    | 'keyNextCamera'
    | 'keyPointCloudSelect'
    | 'keyPointCloudCreateCuboid';

export interface ShortcutSettingConfig {
    /** Unique HTML id for the control (used by label `for`). */
    id: string;
    /** User-visible label text. */
    label: string;
    /** Key into SettingsDialogShortcutState. */
    key: ShortcutSettingKey;
}

export interface StaticShortcutConfig {
    id: string;
    label: string;
    /** Static display value (not recordable). */
    displayValue: string;
}

/** Recordable shortcuts for navigation and general actions. */
export const generalShortcuts: readonly ShortcutSettingConfig[] = [
    { id: 'hide-annotations', label: 'Hide annotations', key: 'hideAnnotations' },
    { id: 'toggle-edit-mode', label: 'Toggle edit mode', key: 'toggleEditMode' }
] as const;

/** Recordable shortcuts that select a tool in the image annotation toolbar. */
export const toolShortcuts: readonly ShortcutSettingConfig[] = [
    { id: 'toolbar-selection', label: 'Selection', key: 'keyToolbarSelection' },
    { id: 'toolbar-drag', label: 'Drag', key: 'keyToolbarDrag' },
    { id: 'toolbar-bounding-box', label: 'Bounding box', key: 'keyToolbarBoundingBox' },
    {
        id: 'toolbar-segmentation-mask',
        label: 'Mask brush',
        key: 'keyToolbarSegmentationMask'
    },
    { id: 'toolbar-slic', label: 'Superpixel brush', key: 'keyToolbarSlic' },
    { id: 'toolbar-brush-mode', label: 'Brush', key: 'keyToolbarBrush' },
    { id: 'toolbar-eraser-mode', label: 'Eraser', key: 'keyToolbarEraser' }
] as const;

/** Recordable shortcuts of the point cloud workspace. */
export const pointCloudShortcuts: readonly ShortcutSettingConfig[] = [
    { id: 'point-cloud-select', label: 'Select cuboid', key: 'keyPointCloudSelect' },
    { id: 'point-cloud-create-cuboid', label: 'Create cuboid', key: 'keyPointCloudCreateCuboid' },
    { id: 'previous-camera', label: 'Previous camera', key: 'keyPreviousCamera' },
    { id: 'next-camera', label: 'Next camera', key: 'keyNextCamera' }
] as const;

/** Non-recordable general shortcut rows (static display only). */
export const staticGeneralShortcuts: readonly StaticShortcutConfig[] = [
    { id: 'go-back', label: 'Go back', displayValue: 'Escape' }
] as const;

/** Non-recordable tool shortcut rows (static display only). */
export const staticToolShortcuts: readonly StaticShortcutConfig[] = [
    { id: 'change-brush-size', label: 'Brush size', displayValue: 'Alt + scroll' }
] as const;

/** Non-recordable point cloud shortcut rows (static display only). */
export const staticPointCloudShortcuts: readonly StaticShortcutConfig[] = [
    { id: 'open-camera-n', label: 'Open camera 1–9', displayValue: '1–9' },
    { id: 'play-pause', label: 'Play / pause', displayValue: 'Space' },
    { id: 'previous-next-tick', label: 'Previous / next tick', displayValue: '← / →' },
    { id: 'move-camera', label: 'Move camera', displayValue: 'W / A / S / D' },
    { id: 'delete-cuboid', label: 'Delete selected cuboid', displayValue: 'Delete / Backspace' },
    { id: 'cancel-deselect', label: 'Cancel or deselect', displayValue: 'Escape' },
    { id: 'confirm-geometry', label: 'Confirm geometry field', displayValue: 'Enter' },
    { id: 'zoom-timeline', label: 'Zoom timeline', displayValue: 'Ctrl/Cmd + scroll' }
] as const;
