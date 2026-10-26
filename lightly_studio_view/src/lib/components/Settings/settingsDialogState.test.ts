import type { SettingView } from '$lib/api/lightly_studio_local';
import { describe, expect, it } from 'vitest';
import {
    createSettingsDialogFormState,
    createSettingsSavePayload,
    normalizeShortcutKey,
    SettingsDialogState
} from './settingsDialogState.svelte';

type ShortcutKeyboardEvent = Parameters<typeof normalizeShortcutKey>[0];

const TEST_SETTINGS: SettingView = {
    setting_id: '00000000-0000-0000-0000-000000000000',
    grid_view_sample_rendering: 'contain',
    grid_view_thumbnail_quality: 'raw',
    image_interpolation: true,
    key_hide_annotations: 'v',
    key_go_back: 'Escape',
    key_toggle_edit_mode: 'e',
    show_annotation_text_labels: false,
    show_sample_filenames: false,
    show_bounding_boxes_for_segmentation: true,
    enforce_coloring_by_class: false,
    created_at: new Date(),
    updated_at: new Date(),
    key_toolbar_selection: 's',
    key_toolbar_drag: 'd',
    key_toolbar_bounding_box: 'b',
    key_toolbar_segmentation_mask: 'm',
    key_toolbar_brush: 'r',
    key_toolbar_eraser: 'x'
};

describe('createSettingsDialogFormState', () => {
    it('maps all settings fields to form state', () => {
        expect(createSettingsDialogFormState(TEST_SETTINGS)).toEqual({
            shortcutSettings: {
                hideAnnotations: 'v',
                toggleEditMode: 'e',
                keyToolbarSelection: 's',
                keyToolbarDrag: 'd',
                keyToolbarBoundingBox: 'b',
                keyToolbarSegmentationMask: 'm',
                keyToolbarSlic: 'a',
                keyToolbarBrush: 'r',
                keyToolbarEraser: 'x'
            },
            gridViewRendering: 'contain',
            gridViewThumbnailQuality: 'raw',
            imageInterpolation: true,
            showAnnotationTextLabels: false,
            showSampleFilenames: false,
            showBoundingBoxesForSegmentation: true,
            enforceColoringByClass: false
        });
    });
});

describe('createSettingsSavePayload', () => {
    it('creates the exact save payload shape', () => {
        expect(
            createSettingsSavePayload({
                shortcutSettings: {
                    hideAnnotations: 'h',
                    toggleEditMode: 't',
                    keyToolbarSelection: 'a',
                    keyToolbarDrag: 'g',
                    keyToolbarBoundingBox: 'q',
                    keyToolbarSegmentationMask: 'w',
                    keyToolbarSlic: 'f',
                    keyToolbarBrush: 'p',
                    keyToolbarEraser: 'o'
                },
                gridViewRendering: 'cover',
                gridViewThumbnailQuality: 'high',
                imageInterpolation: false,
                showAnnotationTextLabels: true,
                showSampleFilenames: true,
                showBoundingBoxesForSegmentation: false,
                enforceColoringByClass: true
            })
        ).toEqual({
            key_hide_annotations: 'h',
            key_toggle_edit_mode: 't',
            grid_view_sample_rendering: 'cover',
            grid_view_thumbnail_quality: 'high',
            image_interpolation: false,
            show_annotation_text_labels: true,
            show_sample_filenames: true,
            show_bounding_boxes_for_segmentation: false,
            enforce_coloring_by_class: true,
            key_toolbar_selection: 'a',
            key_toolbar_drag: 'g',
            key_toolbar_bounding_box: 'q',
            key_toolbar_segmentation_mask: 'w',
            key_toolbar_slic: 'f',
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

describe('SettingsDialogState', () => {
    it('hydrates form state from settings', () => {
        const state = new SettingsDialogState();
        const customSettings: SettingView = {
            ...TEST_SETTINGS,
            key_hide_annotations: 'h',
            image_interpolation: false,
            grid_view_sample_rendering: 'cover',
            show_annotation_text_labels: true,
            enforce_coloring_by_class: true
        };

        state.hydrate(customSettings);

        expect(state.shortcuts.hideAnnotations).toBe('h');
        expect(state.imageInterpolation).toBe(false);
        expect(state.gridViewRendering).toBe('cover');
        expect(state.showAnnotationTextLabels).toBe(true);
        expect(state.enforceColoringByClass).toBe(true);
    });

    it('clears recording state on clearRecording', () => {
        const state = new SettingsDialogState();
        state.startRecording('hideAnnotations');

        expect(state.recordingShortcut).toBe('hideAnnotations');

        state.clearRecording();

        expect(state.recordingShortcut).toBeNull();
    });

    it('records a shortcut and updates only the targeted key', () => {
        const state = new SettingsDialogState();
        state.hydrate(TEST_SETTINGS);
        state.startRecording('toggleEditMode');

        const event = new KeyboardEvent('keydown', { key: 'q' });
        state.handleKeyDown(event);

        expect(state.shortcuts.toggleEditMode).toBe('q');
        // Other shortcuts remain unchanged
        expect(state.shortcuts.hideAnnotations).toBe('v');
        expect(state.shortcuts.keyToolbarSelection).toBe('s');
        expect(state.recordingShortcut).toBeNull();
    });

    it('cancels recording on Escape', () => {
        const state = new SettingsDialogState();
        state.hydrate(TEST_SETTINGS);
        state.startRecording('hideAnnotations');

        const event = new KeyboardEvent('keydown', { key: 'Escape', cancelable: true });
        state.handleKeyDown(event);

        expect(state.shortcuts.hideAnnotations).toBe('v');
        expect(state.recordingShortcut).toBeNull();
        expect(event.defaultPrevented).toBe(true);
    });

    it('ignores keydown when not recording', () => {
        const state = new SettingsDialogState();
        state.hydrate(TEST_SETTINGS);

        const event = new KeyboardEvent('keydown', { key: 'q' });
        state.handleKeyDown(event);

        // Nothing should change
        expect(state.shortcuts.hideAnnotations).toBe('v');
        expect(state.shortcuts.toggleEditMode).toBe('e');
    });

    it('getSavePayload includes both modified and unmodified fields', () => {
        const state = new SettingsDialogState();
        state.hydrate(TEST_SETTINGS);
        state.shortcuts.hideAnnotations = 'z';
        state.showSampleFilenames = true;
        state.imageInterpolation = false;
        state.enforceColoringByClass = true;

        const payload = state.getSavePayload();

        expect(payload).toEqual(
            expect.objectContaining({
                key_hide_annotations: 'z',
                show_sample_filenames: true,
                image_interpolation: false,
                enforce_coloring_by_class: true,
                grid_view_sample_rendering: 'contain'
            })
        );
    });
});

function createKeyboardEvent(key: string, isCapsLockActive = false): ShortcutKeyboardEvent {
    return {
        key,
        getModifierState: (modifierKey: string) => modifierKey === 'CapsLock' && isCapsLockActive
    };
}
