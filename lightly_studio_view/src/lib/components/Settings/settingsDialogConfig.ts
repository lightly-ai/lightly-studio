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
    | 'keyToolbarEraser';

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

/** Recordable shortcuts that select a tool in the annotation toolbar. */
export const toolShortcuts: readonly ShortcutSettingConfig[] = [
    { id: 'toolbar-selection', label: 'Selection', key: 'keyToolbarSelection' },
    { id: 'toolbar-drag', label: 'Drag', key: 'keyToolbarDrag' },
    { id: 'toolbar-bounding-box', label: 'Bounding box', key: 'keyToolbarBoundingBox' },
    {
        id: 'toolbar-segmentation-mask',
        label: 'Segmentation mask',
        key: 'keyToolbarSegmentationMask'
    },
    { id: 'toolbar-slic', label: 'AI-assisted labeling', key: 'keyToolbarSlic' },
    { id: 'toolbar-brush-mode', label: 'Brush', key: 'keyToolbarBrush' },
    { id: 'toolbar-eraser-mode', label: 'Eraser', key: 'keyToolbarEraser' }
] as const;

/** Non-recordable general shortcut rows (static display only). */
export const staticGeneralShortcuts: readonly StaticShortcutConfig[] = [
    { id: 'go-back', label: 'Go back', displayValue: 'Escape' }
] as const;

/** Non-recordable tool shortcut rows (static display only). */
export const staticToolShortcuts: readonly StaticShortcutConfig[] = [
    { id: 'change-brush-size', label: 'Brush size', displayValue: 'Alt + scroll' }
] as const;
