import { describe, expect, it } from 'vitest';
import {
    createSettingsDialogFormState,
    createSettingsSavePayload,
    createSettingsDialogState,
    normalizeShortcutKey
} from './settingsDialogState.svelte';

type SettingsDialogFormState = ReturnType<typeof createSettingsDialogFormState>;
type ShortcutKeyboardEvent = Parameters<typeof normalizeShortcutKey>[0];

const COMPLETE_SETTINGS = {
    setting_id: '00000000-0000-0000-0000-000000000000',
    grid_view_sample_rendering: 'contain' as const,
    grid_view_thumbnail_quality: 'raw' as const,
    key_hide_annotations: 'v',
    key_go_back: 'Escape',
    key_toggle_edit_mode: 'e',
    show_annotation_text_labels: false,
    show_sample_filenames: false,
    show_bounding_boxes_for_segmentation: true,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    key_toolbar_selection: 's',
    key_toolbar_drag: 'd',
    key_toolbar_bounding_box: 'b',
    key_toolbar_segmentation_mask: 'm',
    key_toolbar_brush: 'r',
    key_toolbar_eraser: 'x'
};

describe('createSettingsDialogFormState', () => {
    it('maps settings to dialog defaults', () => {
        expect(createSettingsDialogFormState(COMPLETE_SETTINGS)).toEqual({
            shortcutSettings: {
                hideAnnotations: 'v',
                goBack: 'Escape',
                toggleEditMode: 'e',
                keyToolbarSelection: 's',
                keyToolbarDrag: 'd',
                keyToolbarBoundingBox: 'b',
                keyToolbarSegmentationMask: 'm',
                keyToolbarBrush: 'r',
                keyToolbarEraser: 'x'
            },
            gridViewRendering: 'contain',
            gridViewThumbnailQuality: 'raw',
            showAnnotationTextLabels: false,
            showSampleFilenames: false,
            showBoundingBoxesForSegmentation: true
        });
    });

    it('creates the exact save payload shape', () => {
        const formState: SettingsDialogFormState = {
            shortcutSettings: {
                hideAnnotations: 'h',
                goBack: 'Backspace',
                toggleEditMode: 't',
                keyToolbarSelection: 'a',
                keyToolbarDrag: 'g',
                keyToolbarBoundingBox: 'q',
                keyToolbarSegmentationMask: 'w',
                keyToolbarBrush: 'p',
                keyToolbarEraser: 'o'
            },
            gridViewRendering: 'cover',
            gridViewThumbnailQuality: 'high',
            showAnnotationTextLabels: true,
            showSampleFilenames: true,
            showBoundingBoxesForSegmentation: false
        };

        expect(createSettingsSavePayload(formState)).toEqual({
            key_hide_annotations: 'h',
            key_go_back: 'Backspace',
            key_toggle_edit_mode: 't',
            grid_view_sample_rendering: 'cover',
            grid_view_thumbnail_quality: 'high',
            show_annotation_text_labels: true,
            show_sample_filenames: true,
            show_bounding_boxes_for_segmentation: false,
            key_toolbar_selection: 'a',
            key_toolbar_drag: 'g',
            key_toolbar_bounding_box: 'q',
            key_toolbar_segmentation_mask: 'w',
            key_toolbar_brush: 'p',
            key_toolbar_eraser: 'o'
        });
    });
});

describe('normalizeShortcutKey', () => {
    it('normalizes space to the Space key name', () => {
        expect(normalizeShortcutKey(createKeyboardEvent(' '))).toBe('Space');
    });

    it('normalizes lowercase letters as lowercase', () => {
        expect(normalizeShortcutKey(createKeyboardEvent('a'))).toBe('a');
    });

    it('keeps uppercase letters when caps lock is active', () => {
        expect(normalizeShortcutKey(createKeyboardEvent('A', true))).toBe('A');
    });

    it('keeps non-letter keys unchanged', () => {
        expect(normalizeShortcutKey(createKeyboardEvent('Escape'))).toBe('Escape');
    });
});

describe('createSettingsDialogState', () => {
    it('hydrates form state from settings', () => {
        const state = createSettingsDialogState(COMPLETE_SETTINGS);

        const updatedSettings = {
            ...COMPLETE_SETTINGS,
            key_hide_annotations: 'h',
            grid_view_sample_rendering: 'cover' as const
        };

        state.hydrate(updatedSettings);

        expect(state.shortcutState.hideAnnotations).toBe('h');
        expect(state.gridViewRendering).toBe('cover');
    });

    it('hydrates from async settings while form state is pristine', () => {
        const state = createSettingsDialogState(COMPLETE_SETTINGS);
        const updatedSettings = {
            ...COMPLETE_SETTINGS,
            show_sample_filenames: true
        };

        state.hydrateIfPristine(updatedSettings);

        expect(state.showSampleFilenames).toBe(true);
        expect(state.isDirty).toBe(false);
    });

    it('does not hydrate from async settings after user edits', () => {
        const state = createSettingsDialogState(COMPLETE_SETTINGS);
        state.showSampleFilenames = true;

        state.hydrateIfPristine({
            ...COMPLETE_SETTINGS,
            show_sample_filenames: false,
            key_hide_annotations: 'h'
        });

        expect(state.showSampleFilenames).toBe(true);
        expect(state.shortcutState.hideAnnotations).toBe('v');
        expect(state.isDirty).toBe(true);
    });

    it('clears recording state on close', () => {
        const state = createSettingsDialogState(COMPLETE_SETTINGS);
        state.startRecording('hideAnnotations');
        expect(state.recordingShortcut).toBe('hideAnnotations');

        state.onClose();
        expect(state.recordingShortcut).toBeNull();
        expect(state.isDirty).toBe(false);
    });

    it('records a shortcut for only the targeted key', () => {
        const state = createSettingsDialogState(COMPLETE_SETTINGS);
        state.startRecording('goBack');

        state.handleKeyDown(new KeyboardEvent('keydown', { key: 'q', cancelable: true }));

        expect(state.shortcutState.goBack).toBe('q');
        expect(state.shortcutState.hideAnnotations).toBe('v');
        expect(state.recordingShortcut).toBeNull();
        expect(state.isDirty).toBe(true);
    });

    it('returns save payload with current form values', () => {
        const state = createSettingsDialogState(COMPLETE_SETTINGS);
        state.showAnnotationTextLabels = true;

        const payload = state.getSavePayload();
        expect(payload.show_annotation_text_labels).toBe(true);
        expect(payload.key_hide_annotations).toBe('v');
    });

    it('ignores keydown when not recording', () => {
        const state = createSettingsDialogState(COMPLETE_SETTINGS);

        state.handleKeyDown(new KeyboardEvent('keydown', { key: 'q', cancelable: true }));

        // All shortcuts unchanged
        expect(state.shortcutState.hideAnnotations).toBe('v');
        expect(state.shortcutState.goBack).toBe('Escape');
    });
});

function createKeyboardEvent(key: string, isCapsLockActive = false): ShortcutKeyboardEvent {
    return {
        key,
        getModifierState: (modifierKey: string) => modifierKey === 'CapsLock' && isCapsLockActive
    };
}
