import type {
    GridViewSampleRenderingType,
    GridViewThumbnailQualityType,
    SettingView
} from '$lib/api/lightly_studio_local';
import type { ShortcutSettingKey } from './settingsDialogConfig';

type RenderingMode = GridViewSampleRenderingType;
type ThumbnailQualityMode = GridViewThumbnailQualityType;

interface SettingsDialogShortcutState {
    hideAnnotations: string;
    toggleEditMode: string;
    keyToolbarSelection: string;
    keyToolbarDrag: string;
    keyToolbarBoundingBox: string;
    keyToolbarSegmentationMask: string;
    keyToolbarSlic: string;
    keyToolbarBrush: string;
    keyToolbarEraser: string;
    keyPreviousCamera: string;
    keyNextCamera: string;
    keyPointCloudSelect: string;
    keyPointCloudCreateCuboid: string;
}

interface SettingsDialogFormState {
    shortcutSettings: SettingsDialogShortcutState;
    gridViewRendering: RenderingMode;
    gridViewThumbnailQuality: ThumbnailQualityMode;
    imageInterpolation: boolean;
    showAnnotationTextLabels: boolean;
    showSampleFilenames: boolean;
    showBoundingBoxesForSegmentation: boolean;
    enforceColoringByClass: boolean;
}

interface ShortcutKeyboardEvent {
    key: string;
    getModifierState(key: string): boolean;
}

export function createSettingsDialogFormState(settings: SettingView): SettingsDialogFormState {
    return {
        shortcutSettings: {
            hideAnnotations: settings.key_hide_annotations,
            toggleEditMode: settings.key_toggle_edit_mode,
            keyToolbarSelection: settings.key_toolbar_selection,
            keyToolbarDrag: settings.key_toolbar_drag,
            keyToolbarBoundingBox: settings.key_toolbar_bounding_box,
            keyToolbarSegmentationMask: settings.key_toolbar_segmentation_mask,
            keyToolbarSlic: settings.key_toolbar_slic ?? 'a',
            keyToolbarBrush: settings.key_toolbar_brush,
            keyToolbarEraser: settings.key_toolbar_eraser,
            keyPreviousCamera: settings.key_previous_camera,
            keyNextCamera: settings.key_next_camera,
            keyPointCloudSelect: settings.key_point_cloud_select,
            keyPointCloudCreateCuboid: settings.key_point_cloud_create_cuboid
        },
        gridViewRendering: settings.grid_view_sample_rendering,
        gridViewThumbnailQuality: settings.grid_view_thumbnail_quality,
        imageInterpolation: settings.image_interpolation,
        showAnnotationTextLabels: settings.show_annotation_text_labels,
        showSampleFilenames: settings.show_sample_filenames,
        showBoundingBoxesForSegmentation: settings.show_bounding_boxes_for_segmentation,
        enforceColoringByClass: settings.enforce_coloring_by_class
    };
}

export function createSettingsSavePayload(
    formState: SettingsDialogFormState
): Partial<SettingView> {
    return {
        key_hide_annotations: formState.shortcutSettings.hideAnnotations,
        key_toggle_edit_mode: formState.shortcutSettings.toggleEditMode,
        grid_view_sample_rendering: formState.gridViewRendering,
        grid_view_thumbnail_quality: formState.gridViewThumbnailQuality,
        image_interpolation: formState.imageInterpolation,
        show_annotation_text_labels: formState.showAnnotationTextLabels,
        show_sample_filenames: formState.showSampleFilenames,
        show_bounding_boxes_for_segmentation: formState.showBoundingBoxesForSegmentation,
        enforce_coloring_by_class: formState.enforceColoringByClass,
        key_toolbar_selection: formState.shortcutSettings.keyToolbarSelection,
        key_toolbar_drag: formState.shortcutSettings.keyToolbarDrag,
        key_toolbar_bounding_box: formState.shortcutSettings.keyToolbarBoundingBox,
        key_toolbar_segmentation_mask: formState.shortcutSettings.keyToolbarSegmentationMask,
        key_toolbar_slic: formState.shortcutSettings.keyToolbarSlic,
        key_toolbar_brush: formState.shortcutSettings.keyToolbarBrush,
        key_toolbar_eraser: formState.shortcutSettings.keyToolbarEraser,
        key_previous_camera: formState.shortcutSettings.keyPreviousCamera,
        key_next_camera: formState.shortcutSettings.keyNextCamera,
        key_point_cloud_select: formState.shortcutSettings.keyPointCloudSelect,
        key_point_cloud_create_cuboid: formState.shortcutSettings.keyPointCloudCreateCuboid
    };
}

// A modifier alone is never a shortcut: AltGr and Shift come before the character they type.
const MODIFIER_KEYS = new Set(['Alt', 'AltGraph', 'Control', 'Meta', 'Shift']);
const POINT_CLOUD_SHORTCUTS = new Set<ShortcutSettingKey>([
    'keyPreviousCamera',
    'keyNextCamera',
    'keyPointCloudSelect',
    'keyPointCloudCreateCuboid'
]);
// Fixed keys of the point cloud workspace: playback, ticks, camera movement, confirm, delete,
// and open camera 1–9. A point cloud shortcut on one of them would fire both actions.
const RESERVED_POINT_CLOUD_KEYS = new Set([
    ' ',
    'ArrowLeft',
    'ArrowRight',
    'w',
    'a',
    's',
    'd',
    'Enter',
    'Delete',
    'Backspace',
    ...'123456789'
]);

export function normalizeShortcutKey(event: ShortcutKeyboardEvent): string {
    if (event.key === ' ') {
        return 'Space';
    }

    if (!/^[a-zA-Z]$/.test(event.key)) {
        return event.key;
    }

    if (event.getModifierState('CapsLock')) {
        return event.key;
    }

    return event.key.toLowerCase();
}

/**
 * Reactive state machine for the settings dialog.
 *
 * Encapsulates form values, shortcut recording, and save payload construction.
 * Hydrate from the settings store each time the dialog opens.
 */
export class SettingsDialogState {
    shortcuts = $state<SettingsDialogShortcutState>({
        hideAnnotations: 'v',
        toggleEditMode: 'e',
        keyToolbarSelection: 's',
        keyToolbarDrag: 'd',
        keyToolbarBoundingBox: 'b',
        keyToolbarSegmentationMask: 'm',
        keyToolbarSlic: 'a',
        keyToolbarBrush: 'r',
        keyToolbarEraser: 'x',
        keyPreviousCamera: '[',
        keyNextCamera: ']',
        keyPointCloudSelect: 'q',
        keyPointCloudCreateCuboid: 'c'
    });
    gridViewRendering: RenderingMode = $state('contain');
    gridViewThumbnailQuality: ThumbnailQualityMode = $state('raw');
    imageInterpolation = $state(true);
    showAnnotationTextLabels = $state(false);
    showSampleFilenames = $state(false);
    showBoundingBoxesForSegmentation = $state(true);
    enforceColoringByClass = $state(false);
    recordingShortcut: ShortcutSettingKey | null = $state(null);
    isSaving = $state(false);
    // Payload of the last hydrated settings, to detect unsaved changes.
    savedPayload: Partial<SettingView> = $state(this.getSavePayload());

    /** Whether any form value differs from the hydrated settings. */
    get hasChanges(): boolean {
        const payload = this.getSavePayload();
        return Object.entries(payload).some(
            ([key, value]) => this.savedPayload[key as keyof SettingView] !== value
        );
    }

    /** Populate form fields from the latest store values. */
    hydrate(settings: SettingView): void {
        const formState = createSettingsDialogFormState(settings);
        this.shortcuts = formState.shortcutSettings;
        this.gridViewRendering = formState.gridViewRendering;
        this.gridViewThumbnailQuality = formState.gridViewThumbnailQuality;
        this.imageInterpolation = formState.imageInterpolation;
        this.showAnnotationTextLabels = formState.showAnnotationTextLabels;
        this.showSampleFilenames = formState.showSampleFilenames;
        this.showBoundingBoxesForSegmentation = formState.showBoundingBoxesForSegmentation;
        this.enforceColoringByClass = formState.enforceColoringByClass;
        this.savedPayload = createSettingsSavePayload(formState);
    }

    startRecording(key: ShortcutSettingKey): void {
        this.recordingShortcut = key;
    }

    handleKeyDown(event: KeyboardEvent): void {
        if (!this.recordingShortcut) return;

        event.preventDefault();
        event.stopPropagation();

        // Keep recording until the key that the modifier changes.
        if (MODIFIER_KEYS.has(event.key)) return;
        // Keep recording until a key that the point cloud workspace does not use already.
        if (this.isKeyTakenInPointCloud(this.recordingShortcut, event.key)) return;

        // Escape cancels recording. Stopping it also keeps the dialog open.
        if (event.key !== 'Escape') {
            this.shortcuts[this.recordingShortcut] = normalizeShortcutKey(event);
        }
        this.recordingShortcut = null;
    }

    /**
     * Whether the point cloud workspace already uses the key for another action: a fixed key,
     * the edit mode key, or another point cloud shortcut.
     */
    private isKeyTakenInPointCloud(shortcut: ShortcutSettingKey, key: string): boolean {
        const lowerKey = key.toLowerCase();
        if (shortcut === 'toggleEditMode') return this.isPointCloudShortcutKey(lowerKey, shortcut);
        if (!POINT_CLOUD_SHORTCUTS.has(shortcut)) return false;
        const isFixedKey =
            RESERVED_POINT_CLOUD_KEYS.has(key) || RESERVED_POINT_CLOUD_KEYS.has(lowerKey);
        const isEditModeKey = lowerKey === this.shortcuts.toggleEditMode.toLowerCase();
        return isFixedKey || isEditModeKey || this.isPointCloudShortcutKey(lowerKey, shortcut);
    }

    private isPointCloudShortcutKey(lowerKey: string, recording: ShortcutSettingKey): boolean {
        return [...POINT_CLOUD_SHORTCUTS].some(
            (shortcut) =>
                shortcut !== recording && this.shortcuts[shortcut].toLowerCase() === lowerKey
        );
    }

    clearRecording(): void {
        this.recordingShortcut = null;
    }

    getSavePayload(): Partial<SettingView> {
        return createSettingsSavePayload({
            shortcutSettings: this.shortcuts,
            gridViewRendering: this.gridViewRendering,
            gridViewThumbnailQuality: this.gridViewThumbnailQuality,
            imageInterpolation: this.imageInterpolation,
            showAnnotationTextLabels: this.showAnnotationTextLabels,
            showSampleFilenames: this.showSampleFilenames,
            showBoundingBoxesForSegmentation: this.showBoundingBoxesForSegmentation,
            enforceColoringByClass: this.enforceColoringByClass
        });
    }
}
