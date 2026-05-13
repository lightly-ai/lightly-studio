import type {
    GridViewSampleRenderingType,
    GridViewThumbnailQualityType
} from '$lib/api/lightly_studio_local';
import type { SettingView } from '$lib/hooks/useSettings';
import type { ShortcutSettingKey } from './settingsDialogConfig';

type ShortcutState = Record<ShortcutSettingKey, string>;

interface ShortcutKeyboardEvent {
    key: string;
    getModifierState(key: string): boolean;
}

export function createSettingsDialogFormState(settings: SettingView) {
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
        } satisfies ShortcutState,
        gridViewRendering: settings.grid_view_sample_rendering,
        gridViewThumbnailQuality: settings.grid_view_thumbnail_quality,
        showAnnotationTextLabels: settings.show_annotation_text_labels,
        showSampleFilenames: settings.show_sample_filenames,
        showBoundingBoxesForSegmentation: settings.show_bounding_boxes_for_segmentation
    };
}

export function createSettingsSavePayload(
    formState: ReturnType<typeof createSettingsDialogFormState>
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

function isGridViewSampleRenderingType(value: string): value is GridViewSampleRenderingType {
    return value === 'contain' || value === 'cover';
}

function isGridViewThumbnailQualityType(value: string): value is GridViewThumbnailQualityType {
    return value === 'raw' || value === 'high';
}

/**
 * Reactive state machine for the settings dialog.
 *
 * Encapsulates form state, shortcut recording, and hydration logic.
 * Call `hydrate()` each time the dialog opens to sync with the latest store values.
 */
export function createSettingsDialogState(initialSettings: SettingView) {
    const initial = createSettingsDialogFormState(initialSettings);

    let shortcutState = $state(initial.shortcutSettings);
    let gridViewRendering: GridViewSampleRenderingType = $state(initial.gridViewRendering);
    let gridViewThumbnailQuality: GridViewThumbnailQualityType = $state(
        initial.gridViewThumbnailQuality
    );
    let showAnnotationTextLabels = $state(initial.showAnnotationTextLabels);
    let showSampleFilenames = $state(initial.showSampleFilenames);
    let showBoundingBoxesForSegmentation = $state(initial.showBoundingBoxesForSegmentation);
    let recordingShortcut: ShortcutSettingKey | null = $state(null);
    let isSaving = $state(false);
    let isDirty = $state(false);

    function markDirty() {
        isDirty = true;
    }

    function applyFormState(formState: ReturnType<typeof createSettingsDialogFormState>) {
        shortcutState = formState.shortcutSettings;
        gridViewRendering = formState.gridViewRendering;
        gridViewThumbnailQuality = formState.gridViewThumbnailQuality;
        showAnnotationTextLabels = formState.showAnnotationTextLabels;
        showSampleFilenames = formState.showSampleFilenames;
        showBoundingBoxesForSegmentation = formState.showBoundingBoxesForSegmentation;
    }

    function hydrate(settings: SettingView) {
        applyFormState(createSettingsDialogFormState(settings));
        isDirty = false;
    }

    function hydrateIfPristine(settings: SettingView) {
        if (isDirty) return;
        hydrate(settings);
    }

    function setGridViewRendering(value: string) {
        if (!isGridViewSampleRenderingType(value)) return;
        gridViewRendering = value;
        markDirty();
    }

    function setGridViewThumbnailQuality(value: string) {
        if (!isGridViewThumbnailQualityType(value)) return;
        gridViewThumbnailQuality = value;
        markDirty();
    }

    function startRecording(key: ShortcutSettingKey) {
        recordingShortcut = key;
    }

    function handleKeyDown(event: KeyboardEvent) {
        if (!recordingShortcut) return;
        event.preventDefault();
        event.stopPropagation();
        shortcutState[recordingShortcut] = normalizeShortcutKey(event);
        recordingShortcut = null;
        markDirty();
    }

    function onClose() {
        recordingShortcut = null;
        isDirty = false;
    }

    function getSavePayload(): Partial<SettingView> {
        return createSettingsSavePayload({
            shortcutSettings: shortcutState,
            gridViewRendering,
            gridViewThumbnailQuality,
            showAnnotationTextLabels,
            showSampleFilenames,
            showBoundingBoxesForSegmentation
        });
    }

    return {
        get shortcutState() {
            return shortcutState;
        },
        get gridViewRendering() {
            return gridViewRendering;
        },
        get gridViewThumbnailQuality() {
            return gridViewThumbnailQuality;
        },
        get showAnnotationTextLabels() {
            return showAnnotationTextLabels;
        },
        set showAnnotationTextLabels(value: boolean) {
            showAnnotationTextLabels = value;
            markDirty();
        },
        get showSampleFilenames() {
            return showSampleFilenames;
        },
        set showSampleFilenames(value: boolean) {
            showSampleFilenames = value;
            markDirty();
        },
        get showBoundingBoxesForSegmentation() {
            return showBoundingBoxesForSegmentation;
        },
        set showBoundingBoxesForSegmentation(value: boolean) {
            showBoundingBoxesForSegmentation = value;
            markDirty();
        },
        get recordingShortcut() {
            return recordingShortcut;
        },
        get isSaving() {
            return isSaving;
        },
        set isSaving(value: boolean) {
            isSaving = value;
        },
        get isDirty() {
            return isDirty;
        },
        hydrate,
        hydrateIfPristine,
        setGridViewRendering,
        setGridViewThumbnailQuality,
        startRecording,
        handleKeyDown,
        onClose,
        getSavePayload
    };
}
