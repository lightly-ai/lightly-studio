/**
 * Configuration for the shortcut settings rows displayed in SettingsDialog.
 *
 * Each entry maps a unique HTML id and user-visible label to a key in the
 * ShortcutState managed by settingsDialogState.ts.
 */

/** Keys of the shortcut state object that can be recorded by the user. */
export type ShortcutSettingKey =
    | 'hideAnnotations'
    | 'goBack'
    | 'toggleEditMode'
    | 'keyToolbarSelection'
    | 'keyToolbarDrag'
    | 'keyToolbarBoundingBox'
    | 'keyToolbarSegmentationMask'
    | 'keyToolbarBrush'
    | 'keyToolbarEraser';

export interface ShortcutSettingConfig {
    /** Unique HTML id for the control (used by label `for`). */
    id: string;
    /** User-visible label text. */
    label: string;
    /** Key into ShortcutState. */
    key: ShortcutSettingKey;
}

export interface StaticShortcutConfig {
    id: string;
    label: string;
    /** Static display value (not recordable). */
    displayValue: string;
}

/** Recordable shortcut rows shown in the Keyboard Shortcuts section. */
export const shortcutSettings: readonly ShortcutSettingConfig[] = [
    { id: 'hide-annotations', label: 'Hide Annotations', key: 'hideAnnotations' },
    { id: 'go-back', label: 'Go Back', key: 'goBack' },
    { id: 'toggle-edit-mode', label: 'Toggle Edit Mode', key: 'toggleEditMode' },
    { id: 'toolbar-selection', label: 'Toolbar selection', key: 'keyToolbarSelection' },
    { id: 'toolbar-drag', label: 'Toolbar drag', key: 'keyToolbarDrag' },
    { id: 'toolbar-bounding-box', label: 'Toolbar bounding box', key: 'keyToolbarBoundingBox' },
    {
        id: 'toolbar-segmentation-mask',
        label: 'Toolbar segmentation mask',
        key: 'keyToolbarSegmentationMask'
    },
    { id: 'toolbar-brush-mode', label: 'Toolbar brush mode', key: 'keyToolbarBrush' },
    { id: 'toolbar-eraser-mode', label: 'Toolbar eraser mode', key: 'keyToolbarEraser' }
] as const;

/** Non-recordable shortcut rows (static display only). */
export const staticShortcuts: readonly StaticShortcutConfig[] = [
    { id: 'change-brush-size', label: 'Change brush size', displayValue: 'Alt + scroll' }
] as const;
