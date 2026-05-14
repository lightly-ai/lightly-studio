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
    goBack: string;
    toggleEditMode: string;
    keyToolbarSelection: string;
    keyToolbarDrag: string;
    keyToolbarBoundingBox: string;
    keyToolbarSegmentationMask: string;
    keyToolbarBrush: string;
    keyToolbarEraser: string;
}

interface SettingsDialogFormState {
    shortcutSettings: SettingsDialogShortcutState;
    gridViewRendering: RenderingMode;
    gridViewThumbnailQuality: ThumbnailQualityMode;
    showAnnotationTextLabels: boolean;
    showSampleFilenames: boolean;
    showBoundingBoxesForSegmentation: boolean;
}

interface ShortcutKeyboardEvent {
    key: string;
    getModifierState(key: string): boolean;
}

export function createSettingsDialogFormState(settings: SettingView): SettingsDialogFormState {
    return {
        shortcutSettings: {
            hideAnnotations: settings.key_hide_annotations,
            goBack: settings.key_go_back,
            toggleEditMode: settings.key_toggle_edit_mode,
            keyToolbarSelection: settings.key_toolbar_selection,
            keyToolbarDrag: settings.key_toolbar_drag,
            keyToolbarBoundingBox: settings.key_toolbar_bounding_box,
            keyToolbarSegmentationMask: settings.key_toolbar_segmentation_mask,
            keyToolbarBrush: settings.key_toolbar_brush,
            keyToolbarEraser: settings.key_toolbar_eraser
        },
        gridViewRendering: settings.grid_view_sample_rendering,
        gridViewThumbnailQuality: settings.grid_view_thumbnail_quality,
        showAnnotationTextLabels: settings.show_annotation_text_labels,
        showSampleFilenames: settings.show_sample_filenames,
        showBoundingBoxesForSegmentation: settings.show_bounding_boxes_for_segmentation
    };
}

export function createSettingsSavePayload(
    formState: SettingsDialogFormState
): Partial<SettingView> {
    return {
        key_hide_annotations: formState.shortcutSettings.hideAnnotations,
        key_go_back: formState.shortcutSettings.goBack,
        key_toggle_edit_mode: formState.shortcutSettings.toggleEditMode,
        grid_view_sample_rendering: formState.gridViewRendering,
        grid_view_thumbnail_quality: formState.gridViewThumbnailQuality,
        show_annotation_text_labels: formState.showAnnotationTextLabels,
        show_sample_filenames: formState.showSampleFilenames,
        show_bounding_boxes_for_segmentation: formState.showBoundingBoxesForSegmentation,
        key_toolbar_selection: formState.shortcutSettings.keyToolbarSelection,
        key_toolbar_drag: formState.shortcutSettings.keyToolbarDrag,
        key_toolbar_bounding_box: formState.shortcutSettings.keyToolbarBoundingBox,
        key_toolbar_segmentation_mask: formState.shortcutSettings.keyToolbarSegmentationMask,
        key_toolbar_brush: formState.shortcutSettings.keyToolbarBrush,
        key_toolbar_eraser: formState.shortcutSettings.keyToolbarEraser
    };
}

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
        goBack: 'Escape',
        toggleEditMode: 'e',
        keyToolbarSelection: 's',
        keyToolbarDrag: 'd',
        keyToolbarBoundingBox: 'b',
        keyToolbarSegmentationMask: 'm',
        keyToolbarBrush: 'r',
        keyToolbarEraser: 'x'
    });
    gridViewRendering: RenderingMode = $state('contain');
    gridViewThumbnailQuality: ThumbnailQualityMode = $state('raw');
    showAnnotationTextLabels = $state(false);
    showSampleFilenames = $state(false);
    showBoundingBoxesForSegmentation = $state(true);
    recordingShortcut: ShortcutSettingKey | null = $state(null);
    isSaving = $state(false);

    /** Populate form fields from the latest store values. */
    hydrate(settings: SettingView): void {
        const formState = createSettingsDialogFormState(settings);
        this.shortcuts = formState.shortcutSettings;
        this.gridViewRendering = formState.gridViewRendering;
        this.gridViewThumbnailQuality = formState.gridViewThumbnailQuality;
        this.showAnnotationTextLabels = formState.showAnnotationTextLabels;
        this.showSampleFilenames = formState.showSampleFilenames;
        this.showBoundingBoxesForSegmentation = formState.showBoundingBoxesForSegmentation;
    }

    startRecording(key: ShortcutSettingKey): void {
        this.recordingShortcut = key;
    }

    handleKeyDown(event: KeyboardEvent): void {
        if (!this.recordingShortcut) return;

        event.preventDefault();
        event.stopPropagation();

        this.shortcuts[this.recordingShortcut] = normalizeShortcutKey(event);
        this.recordingShortcut = null;
    }

    clearRecording(): void {
        this.recordingShortcut = null;
    }

    getSavePayload(): Partial<SettingView> {
        return createSettingsSavePayload({
            shortcutSettings: this.shortcuts,
            gridViewRendering: this.gridViewRendering,
            gridViewThumbnailQuality: this.gridViewThumbnailQuality,
            showAnnotationTextLabels: this.showAnnotationTextLabels,
            showSampleFilenames: this.showSampleFilenames,
            showBoundingBoxesForSegmentation: this.showBoundingBoxesForSegmentation
        });
    }
}
