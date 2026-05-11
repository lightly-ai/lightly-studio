import type { components } from '$lib/schema';

type SettingView = components['schemas']['SettingView'];

export type RenderingMode = components['schemas']['GridViewSampleRenderingType'];
export type ThumbnailQualityMode = components['schemas']['GridViewThumbnailQualityType'];

export interface SettingsDialogShortcutState {
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

export type ShortcutSettingKey = keyof SettingsDialogShortcutState;

export interface SettingsDialogFormState {
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

export function createSettingsDialogFormState(
    settings: Partial<SettingView>
): SettingsDialogFormState {
    return {
        shortcutSettings: {
            hideAnnotations: settings.key_hide_annotations || 'v',
            goBack: settings.key_go_back || 'Escape',
            toggleEditMode: settings.key_toggle_edit_mode || 'e',
            keyToolbarSelection: settings.key_toolbar_selection || 's',
            keyToolbarDrag: settings.key_toolbar_drag || 'd',
            keyToolbarBoundingBox: settings.key_toolbar_bounding_box || 'b',
            keyToolbarSegmentationMask: settings.key_toolbar_segmentation_mask || 'm',
            keyToolbarBrush: settings.key_toolbar_brush || 'r',
            keyToolbarEraser: settings.key_toolbar_eraser || 'x'
        },
        gridViewRendering: settings.grid_view_sample_rendering || 'contain',
        gridViewThumbnailQuality: settings.grid_view_thumbnail_quality || 'raw',
        showAnnotationTextLabels: settings.show_annotation_text_labels ?? false,
        showSampleFilenames: settings.show_sample_filenames ?? false,
        showBoundingBoxesForSegmentation: settings.show_bounding_boxes_for_segmentation ?? true
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
