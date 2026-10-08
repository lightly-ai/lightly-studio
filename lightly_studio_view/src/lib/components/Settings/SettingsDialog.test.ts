import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { QueryClient } from '@tanstack/svelte-query';
import { writable } from 'svelte/store';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import SettingsDialogHarness from './SettingsDialogHarness.test.svelte';
import { useSettingsDialog } from '$lib/hooks/useSettingsDialog/useSettingsDialog';
import type { AssistedLabelingProviderView } from '$lib/api/lightly_studio_local';
import { listAssistedLabelingProviders } from '$lib/api/lightly_studio_local/sdk.gen';
import { getAssistedLabelingProviderQueryKey } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';

vi.mock('$lib/api/lightly_studio_local/sdk.gen', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/api/lightly_studio_local/sdk.gen')>()),
    listAssistedLabelingProviders: vi.fn()
}));

const capabilities: AssistedLabelingProviderView['capabilities'] = {
    positive_points: true,
    negative_points: true,
    boxes: true,
    text_prompt: true,
    max_instances: 10
};

const providers: AssistedLabelingProviderView[] = [
    {
        provider_id: 'fal_sam3',
        display_name: 'fal.ai SAM 3',
        sends_data_to_third_party: true,
        capabilities,
        unavailable_reason: 'Set the FAL_KEY environment variable.'
    },
    {
        provider_id: 'fake',
        display_name: 'Fake',
        sends_data_to_third_party: false,
        capabilities,
        unavailable_reason: null
    }
];

let client: QueryClient;

function renderDialog() {
    client = new QueryClient();
    return render(SettingsDialogHarness, { props: { client } });
}

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
        enforce_coloring_by_class: false,
        key_toolbar_selection: 's',
        key_toolbar_drag: 'd',
        key_toolbar_bounding_box: 'b',
        key_toolbar_segmentation_mask: 'm',
        key_toolbar_brush: 'r',
        key_toolbar_eraser: 'x',
        assisted_labeling_provider: 'fal_sam3'
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
        vi.mocked(listAssistedLabelingProviders).mockResolvedValue({
            data: providers
        } as Awaited<ReturnType<typeof listAssistedLabelingProviders>>);
        closeSettingsDialog();
    });

    afterEach(() => {
        document.body.innerHTML = '';
        closeSettingsDialog();
    });

    it('should be closed by default', () => {
        renderDialog();
        expect(
            screen.queryByText('Configure your application preferences.')
        ).not.toBeInTheDocument();
    });

    it('should open the dialog when requested through useSettingsDialog', async () => {
        renderDialog();
        expect(
            screen.queryByText('Configure your application preferences.')
        ).not.toBeInTheDocument();

        await openDialog();

        expect(screen.getByText('Configure your application preferences.')).toBeInTheDocument();
    });

    it('should record and save a keyboard shortcut', async () => {
        renderDialog();
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
        renderDialog();
        await openDialog();

        const toggle = screen.getByRole('switch', { name: 'Show Annotation Class Names' });
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

    it('should show and save the enforce coloring by class switch', async () => {
        renderDialog();
        await openDialog();

        const toggle = screen.getByRole('switch', { name: 'Enforce Coloring by Class' });
        expect(toggle).toHaveAttribute('aria-checked', 'false');

        await fireEvent.click(toggle);
        await fireEvent.click(screen.getByText('Save Changes'));

        const { saveSettings } = useSettings();
        expect(saveSettings).toHaveBeenCalledWith(
            expect.objectContaining({
                enforce_coloring_by_class: true
            })
        );
    });

    it('should save all initial settings unchanged when no edits are made', async () => {
        renderDialog();
        await openDialog();

        await fireEvent.click(screen.getByText('Save Changes'));

        const { saveSettings } = useSettings();
        expect(saveSettings).toHaveBeenCalledWith({
            key_hide_annotations: 'v',
            key_go_back: 'Escape',
            key_toggle_edit_mode: 'e',
            grid_view_sample_rendering: 'contain',
            grid_view_thumbnail_quality: 'raw',
            show_annotation_text_labels: false,
            show_sample_filenames: true,
            show_bounding_boxes_for_segmentation: true,
            enforce_coloring_by_class: false,
            key_toolbar_selection: 's',
            key_toolbar_drag: 'd',
            key_toolbar_bounding_box: 'b',
            key_toolbar_segmentation_mask: 'm',
            key_toolbar_brush: 'r',
            key_toolbar_eraser: 'x',
            assisted_labeling_provider: 'fal_sam3'
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

        renderDialog();
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
        renderDialog();
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
        renderDialog();
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

    it('should show the selected AI-assisted labeling provider and refresh it after saving', async () => {
        renderDialog();
        await openDialog();

        expect(
            await screen.findByText('Set the FAL_KEY environment variable.')
        ).toBeInTheDocument();
        expect(
            screen.getByText('Images are sent to fal.ai SAM 3 for processing.')
        ).toBeInTheDocument();
        expect(screen.getByLabelText('AI-Assisted Labeling Provider')).toHaveTextContent(
            'fal.ai SAM 3'
        );

        const invalidate = vi.spyOn(client, 'invalidateQueries');
        await fireEvent.click(screen.getByText('Save Changes'));

        const { saveSettings } = useSettings();
        expect(saveSettings).toHaveBeenCalledWith(
            expect.objectContaining({ assisted_labeling_provider: 'fal_sam3' })
        );
        await waitFor(() =>
            expect(invalidate).toHaveBeenCalledWith({
                queryKey: getAssistedLabelingProviderQueryKey()
            })
        );
    });
});
