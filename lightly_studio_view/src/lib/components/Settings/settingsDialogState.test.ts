import { describe, expect, it } from 'vitest';
import {
    createSettingsDialogFormState,
    createSettingsSavePayload,
    normalizeShortcutKey
} from './settingsDialogState';

type ShortcutKeyboardEvent = Parameters<typeof normalizeShortcutKey>[0];

describe('settingsDialogState', () => {
    it('maps missing settings fields to dialog defaults', () => {
        expect(createSettingsDialogFormState({})).toEqual({
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
        expect(
            createSettingsSavePayload({
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
            })
        ).toEqual({
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

function createKeyboardEvent(key: string, isCapsLockActive = false): ShortcutKeyboardEvent {
    return {
        key,
        getModifierState: (modifierKey: string) => modifierKey === 'CapsLock' && isCapsLockActive
    };
}
