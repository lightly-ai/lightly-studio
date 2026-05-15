import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { writable } from 'svelte/store';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import SettingsDialog from './SettingsDialog.svelte';
import { useSettingsDialog } from '$lib/hooks/useSettingsDialog/useSettingsDialog';

// Mock the useSettings hook
vi.mock('$lib/hooks/useSettings', () => {
    const mockSaveSettings = vi.fn().mockResolvedValue({ success: true });

    const settingsStore = writable({
        key_hide_annotations: 'v',
        key_go_back: 'Escape',
        key_toggle_edit_mode: 'e',
        grid_view_sample_rendering: 'contain',
        grid_view_thumbnail_quality: 'raw',
        show_annotation_text_labels: false,
        show_sample_filenames: true,
        show_bounding_boxes_for_segmentation: true,
        key_toolbar_selection: 's',
        key_toolbar_drag: 'd',
        key_toolbar_bounding_box: 'b',
        key_toolbar_segmentation_mask: 'm',
        key_toolbar_brush: 'r',
        key_toolbar_eraser: 'x'
    });
    const isLoadedStore = writable(true);

    return {
        useSettings: () => ({
            settingsStore,
            isLoadedStore,
            saveSettings: mockSaveSettings
        })
    };
});

// Get reference to the mocked function
import { useSettings } from '$lib/hooks/useSettings';
const { openSettingsDialog, closeSettingsDialog } = useSettingsDialog();

async function openDialog() {
    openSettingsDialog();
    await waitFor(() =>
        expect(screen.getByText('Configure your application preferences.')).toBeInTheDocument()
    );
}

describe('SettingsDialog', () => {
    beforeEach(() => {
        vi.resetAllMocks();
        const { saveSettings } = useSettings();
        saveSettings.mockResolvedValue({ success: true });
        closeSettingsDialog();
    });

    afterEach(() => {
        document.body.innerHTML = '';
        closeSettingsDialog();
    });

    it('should be closed by default', () => {
        render(SettingsDialog);
        expect(
            screen.queryByText('Configure your application preferences.')
        ).not.toBeInTheDocument();
    });

    it('should open the dialog when requested through useSettingsDialog', async () => {
        render(SettingsDialog);
        expect(
            screen.queryByText('Configure your application preferences.')
        ).not.toBeInTheDocument();

        await openDialog();

        expect(screen.getByText('Configure your application preferences.')).toBeInTheDocument();
    });

    it('should record and save a keyboard shortcut', async () => {
        render(SettingsDialog);
        await openDialog();

        // Use getByLabelText to find the shortcut button via its <Label for="hide-annotations">
        const shortcutButton = screen.getByLabelText('Hide Annotations');
        await fireEvent.click(shortcutButton);

        expect(screen.getByText('Press a key...')).toBeInTheDocument();

        await fireEvent.keyDown(window, { key: 'z' });
        expect(shortcutButton).toHaveTextContent('z');

        await fireEvent.click(screen.getByText('Save Changes'));

        const { saveSettings } = useSettings();
        expect(saveSettings).toHaveBeenCalledWith(
            expect.objectContaining({
                key_hide_annotations: 'z'
            })
        );
    });

    it('should toggle a switch and save the updated value', async () => {
        render(SettingsDialog);
        await openDialog();

        const toggle = screen.getByRole('switch', { name: 'Show Annotation Text Labels' });
        expect(toggle).toHaveAttribute('aria-checked', 'false');

        await fireEvent.click(toggle);
        await fireEvent.click(screen.getByText('Save Changes'));

        const { saveSettings } = useSettings();
        expect(saveSettings).toHaveBeenCalledWith(
            expect.objectContaining({
                show_annotation_text_labels: true
            })
        );
    });

    it('should save all initial settings unchanged when no edits are made', async () => {
        render(SettingsDialog);
        await openDialog();

        await fireEvent.click(screen.getByText('Save Changes'));

        const { saveSettings } = useSettings();
        expect(saveSettings).toHaveBeenCalledWith(
            expect.objectContaining({
                key_hide_annotations: 'v',
                key_go_back: 'Escape',
                key_toggle_edit_mode: 'e',
                grid_view_sample_rendering: 'contain',
                grid_view_thumbnail_quality: 'raw',
                show_annotation_text_labels: false,
                show_sample_filenames: true,
                show_bounding_boxes_for_segmentation: true
            })
        );
    });

    it('should show saving state while submitting', async () => {
        const { saveSettings } = useSettings();
        let resolvePromise: () => void;
        saveSettings.mockImplementation(
            () =>
                new Promise((resolve) => {
                    resolvePromise = () => resolve({ success: true });
                })
        );

        render(SettingsDialog);
        await openDialog();

        await fireEvent.click(screen.getByText('Save Changes'));
        expect(screen.getByText('Saving...')).toBeInTheDocument();

        resolvePromise!();

        await waitFor(() => {
            expect(
                screen.queryByText('Configure your application preferences.')
            ).not.toBeInTheDocument();
        });
    });

    it('should close without saving when cancel is clicked', async () => {
        render(SettingsDialog);
        await openDialog();

        // Make a change first
        const shortcutButton = screen.getByLabelText('Hide Annotations');
        await fireEvent.click(shortcutButton);
        await fireEvent.keyDown(window, { key: 'z' });

        await fireEvent.click(screen.getByText('Cancel'));

        expect(
            screen.queryByText('Configure your application preferences.')
        ).not.toBeInTheDocument();

        const { saveSettings } = useSettings();
        expect(saveSettings).not.toHaveBeenCalled();
    });

    it('should have unique IDs for all shortcut controls', async () => {
        render(SettingsDialog);
        await openDialog();

        const ids = [
            'hide-annotations',
            'go-back',
            'toggle-edit-mode',
            'toolbar-selection',
            'toolbar-drag',
            'toolbar-bounding-box',
            'toolbar-segmentation-mask',
            'toolbar-brush-mode',
            'toolbar-eraser-mode',
            'change-brush-size'
        ];

        for (const id of ids) {
            const elements = document.querySelectorAll(`#${id}`);
            expect(elements.length, `Expected exactly one element with id="${id}"`).toBe(1);
        }
    });
});
