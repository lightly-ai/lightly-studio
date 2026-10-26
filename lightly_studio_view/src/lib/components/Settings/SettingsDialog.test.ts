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
        image_interpolation: true,
        show_annotation_text_labels: false,
        show_sample_filenames: true,
        show_bounding_boxes_for_segmentation: true,
        enforce_coloring_by_class: false,
        key_toolbar_selection: 's',
        key_toolbar_drag: 'd',
        key_toolbar_bounding_box: 'b',
        key_toolbar_segmentation_mask: 'm',
        key_toolbar_slic: 'a',
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

async function openTab(name: string) {
    await fireEvent.click(screen.getByRole('tab', { name }));
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
        const shortcutButton = screen.getByLabelText('Hide annotations');
        await fireEvent.click(shortcutButton);

        expect(screen.getByText('Press a key...')).toBeInTheDocument();

        await fireEvent.keyDown(document, { key: 'z' });
        expect(shortcutButton).toHaveTextContent('z');

        await fireEvent.click(screen.getByText('Save changes'));

        const { saveSettings } = useSettings();
        expect(saveSettings).toHaveBeenCalledWith(
            expect.objectContaining({
                key_hide_annotations: 'z'
            })
        );
    });

    it('should not pass key presses to app shortcuts while open', async () => {
        const appShortcutHandler = vi.fn();
        window.addEventListener('keydown', appShortcutHandler);
        render(SettingsDialog);
        await openDialog();

        await fireEvent.keyDown(screen.getByRole('dialog'), { key: 'e' });

        expect(appShortcutHandler).not.toHaveBeenCalled();
        window.removeEventListener('keydown', appShortcutHandler);
    });

    it('should close on Escape', async () => {
        render(SettingsDialog);
        await openDialog();

        await fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });

        await waitFor(() =>
            expect(
                screen.queryByText('Configure your application preferences.')
            ).not.toBeInTheDocument()
        );
    });

    it('should show Go back as a fixed Escape shortcut', async () => {
        render(SettingsDialog);
        await openDialog();

        const goBack = screen.getByLabelText('Go back');
        expect(goBack).toHaveTextContent('Escape');
        expect(goBack).toBeDisabled();
    });

    it('should cancel recording on Escape and keep the dialog open', async () => {
        render(SettingsDialog);
        await openDialog();

        const shortcutButton = screen.getByLabelText('Hide annotations');
        await fireEvent.click(shortcutButton);
        await fireEvent.keyDown(document, { key: 'Escape' });

        expect(screen.queryByText('Press a key...')).not.toBeInTheDocument();
        expect(shortcutButton).toHaveTextContent('v');
        expect(screen.getByText('Settings')).toBeInTheDocument();
    });

    it('should open on the Shortcuts tab', async () => {
        render(SettingsDialog);
        await openDialog();
        await openTab('Annotations');
        await fireEvent.click(screen.getByText('Cancel'));
        await openDialog();

        expect(screen.getByRole('tab', { name: 'Shortcuts' })).toHaveAttribute(
            'aria-selected',
            'true'
        );
        expect(screen.queryByRole('switch')).not.toBeInTheDocument();
    });

    it('should keep unsaved changes across tabs and stop recording on tab switch', async () => {
        render(SettingsDialog);
        await openDialog();

        await fireEvent.click(screen.getByLabelText('Hide annotations'));
        await openTab('Annotations');
        await fireEvent.click(screen.getByRole('switch', { name: 'Always color by class' }));
        await fireEvent.keyDown(document, { key: 'z' });
        await openTab('Shortcuts');

        expect(screen.queryByText('Press a key...')).not.toBeInTheDocument();

        await fireEvent.click(screen.getByText('Save changes'));

        const { saveSettings } = useSettings();
        expect(saveSettings).toHaveBeenCalledWith(
            expect.objectContaining({ key_hide_annotations: 'v', enforce_coloring_by_class: true })
        );
    });

    it('should toggle a switch and save the updated value', async () => {
        render(SettingsDialog);
        await openDialog();
        await openTab('Annotations');

        const toggle = screen.getByRole('switch', { name: 'Show annotation class names' });
        expect(toggle).toHaveAttribute('aria-checked', 'false');

        await fireEvent.click(toggle);
        await fireEvent.click(screen.getByText('Save changes'));

        const { saveSettings } = useSettings();
        expect(saveSettings).toHaveBeenCalledWith(
            expect.objectContaining({
                show_annotation_text_labels: true
            })
        );
    });

    it('should show and save the enforce coloring by class switch', async () => {
        render(SettingsDialog);
        await openDialog();
        await openTab('Annotations');

        const toggle = screen.getByRole('switch', { name: 'Always color by class' });
        expect(toggle).toHaveAttribute('aria-checked', 'false');

        await fireEvent.click(toggle);
        await fireEvent.click(screen.getByText('Save changes'));

        const { saveSettings } = useSettings();
        expect(saveSettings).toHaveBeenCalledWith(
            expect.objectContaining({
                enforce_coloring_by_class: true
            })
        );
    });

    it('should disable image interpolation and save the setting', async () => {
        render(SettingsDialog);
        await openDialog();
        await openTab('Display');

        const toggle = screen.getByRole('switch', { name: 'Image interpolation' });
        expect(toggle).toHaveAttribute('aria-checked', 'true');

        await fireEvent.click(toggle);
        await fireEvent.click(screen.getByText('Save changes'));

        const { saveSettings } = useSettings();
        expect(saveSettings).toHaveBeenCalledWith(
            expect.objectContaining({ image_interpolation: false })
        );
    });

    it('should save all initial settings unchanged when no edits are made', async () => {
        render(SettingsDialog);
        await openDialog();

        await fireEvent.click(screen.getByText('Save changes'));

        const { saveSettings } = useSettings();
        expect(saveSettings).toHaveBeenCalledWith({
            key_hide_annotations: 'v',
            key_toggle_edit_mode: 'e',
            grid_view_sample_rendering: 'contain',
            grid_view_thumbnail_quality: 'raw',
            image_interpolation: true,
            show_annotation_text_labels: false,
            show_sample_filenames: true,
            show_bounding_boxes_for_segmentation: true,
            enforce_coloring_by_class: false,
            key_toolbar_selection: 's',
            key_toolbar_drag: 'd',
            key_toolbar_bounding_box: 'b',
            key_toolbar_segmentation_mask: 'm',
            key_toolbar_slic: 'a',
            key_toolbar_brush: 'r',
            key_toolbar_eraser: 'x'
        });
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

        await fireEvent.click(screen.getByText('Save changes'));
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
        const shortcutButton = screen.getByLabelText('Hide annotations');
        await fireEvent.click(shortcutButton);
        await fireEvent.keyDown(document, { key: 'z' });

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
