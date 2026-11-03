import { QueryClient } from '@tanstack/svelte-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
    bulkDeleteAnnotationsByFilter,
    bulkRelabelAnnotations,
    labelCounts,
    moveAnnotations,
    readAnnotationCollections,
    readAnnotationLabels,
    readCollection
} from '$lib/api/lightly_studio_local/sdk.gen';
import { get } from 'svelte/store';
import { useGlobalStorage } from '$lib/hooks';
import AnnotationsAnnotatePopoverHarness from './AnnotationsAnnotatePopoverHarness.svelte';

const ids = ['a1', 'a2', 'a3', 'a4'];
const mocks = vi.hoisted(() => ({ target: {} as unknown }));

vi.mock('$lib/api/lightly_studio_local/sdk.gen', async () => ({
    ...(await vi.importActual('$lib/api/lightly_studio_local/sdk.gen')),
    labelCounts: vi.fn(),
    readAnnotationLabels: vi.fn(),
    readAnnotationCollections: vi.fn(),
    readCollection: vi.fn(),
    bulkDeleteAnnotationsByFilter: vi.fn(),
    bulkRelabelAnnotations: vi.fn(),
    bulkRelabelAnnotationsByFilter: vi.fn(),
    moveAnnotations: vi.fn(),
    getAnalyticsConfig: vi.fn().mockResolvedValue({})
}));
vi.mock('svelte-sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }));
vi.mock('$app/state', () => ({ page: { params: { dataset_id: 'root' } } }));
vi.mock('$lib/hooks/useSelectionTarget/useSelectionTarget', () => ({
    getSelectionTarget: () => mocks.target
}));

function setup() {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(AnnotationsAnnotatePopoverHarness, { client, selectedCount: 4 });
}

beforeEach(() => {
    vi.clearAllMocks();
    mocks.target = { kind: 'ids', ids };
    const storage = useGlobalStorage();
    storage.clearSelectedSampleAnnotationCrops('c1');
    storage.clearReversibleActions();
    ids.forEach((id) => storage.toggleSampleAnnotationCropSelection('c1', id));
    vi.mocked(labelCounts).mockResolvedValue({
        data: [
            { annotation_label_id: 'l-deer', label_name: 'deer', count: 3 },
            { annotation_label_id: 'l-fox', label_name: 'fox', count: 1 }
        ]
    } as never);
    vi.mocked(readAnnotationLabels).mockResolvedValue({
        data: [
            { annotation_label_id: 'l-deer', annotation_label_name: 'deer', dataset_id: 'd' },
            { annotation_label_id: 'l-raccoon', annotation_label_name: 'raccoon', dataset_id: 'd' }
        ]
    } as never);
    vi.mocked(readCollection).mockResolvedValue({
        data: { collection_id: 'c1', parent_collection_id: 'owner' }
    } as never);
    vi.mocked(readAnnotationCollections).mockResolvedValue({
        data: [
            { collection_id: 'c1', name: 'ground_truth' },
            { collection_id: 'c2', name: 'predictions' }
        ]
    } as never);
    vi.mocked(bulkDeleteAnnotationsByFilter).mockResolvedValue({
        data: { deleted_count: 1 }
    } as never);
    vi.mocked(bulkRelabelAnnotations).mockResolvedValue({
        data: { previous_labels: [{ annotation_id: 'a1', label_name: 'deer' }] }
    } as never);
    vi.mocked(moveAnnotations).mockResolvedValue({ data: { moved_count: 4 } } as never);
});

describe('AnnotationsAnnotatePopover', () => {
    it('shows the header and the class counts from label_counts', async () => {
        setup();
        expect(screen.getByText('All 4 selected')).toBeInTheDocument();
        expect(await screen.findByText('deer')).toBeInTheDocument();
        expect(screen.getByText('3')).toBeInTheDocument();
        expect(screen.getByText('fox')).toBeInTheDocument();
        expect(screen.getByText('1')).toBeInTheDocument();
        expect(labelCounts).toHaveBeenCalledWith(
            expect.objectContaining({
                body: {
                    filter: { filter_type: 'annotations', sample_ids: ids, collection_ids: ['c1'] }
                }
            })
        );
    });

    it('keeps a select-all snapshot filter for the counts', async () => {
        const filter = { filter_type: 'annotations', collection_ids: ['c1'], tag_ids: ['t'] };
        mocks.target = { kind: 'filter', filter, size: 4 };
        setup();
        await screen.findByText('deer');
        expect(labelCounts).toHaveBeenCalledWith(expect.objectContaining({ body: { filter } }));
    });

    it('trash opens the delete dialog and deletes the class by filter', async () => {
        setup();
        await fireEvent.click(await screen.findByLabelText('Delete fox annotations'));
        expect(await screen.findByText('Delete 1 annotation?')).toBeInTheDocument();
        await fireEvent.click(screen.getByRole('button', { name: 'Delete' }));
        await waitFor(() =>
            expect(bulkDeleteAnnotationsByFilter).toHaveBeenCalledWith({
                path: { collection_id: 'c1' },
                body: {
                    filter: {
                        filter_type: 'annotations',
                        sample_ids: ids,
                        collection_ids: ['c1'],
                        annotation_label_ids: ['l-fox']
                    }
                }
            })
        );
    });

    it('relabels the whole selection to an existing or a new class', async () => {
        setup();
        const user = userEvent.setup();
        const input = screen.getByPlaceholderText('Relabel all to…');
        await user.type(input, 'raccoon');
        await user.click(await screen.findByRole('option', { name: 'raccoon' }));
        await waitFor(() =>
            expect(bulkRelabelAnnotations).toHaveBeenCalledWith({
                path: { collection_id: 'c1' },
                body: { annotation_ids: ids, label_name: 'raccoon' }
            })
        );
        expect(get(useGlobalStorage().reversibleActions)).toEqual([
            expect.objectContaining({ groupId: 'annotation-label-change' })
        ]);

        ids.forEach((id) => useGlobalStorage().toggleSampleAnnotationCropSelection('c1', id));
        await user.clear(input);
        await user.type(input, 'wolf');
        await user.click(await screen.findByText("Create 'wolf'"));
        await waitFor(() =>
            expect(bulkRelabelAnnotations).toHaveBeenLastCalledWith({
                path: { collection_id: 'c1' },
                body: { annotation_ids: ids, label_name: 'wolf' }
            })
        );
    });

    it('moves the selection to the picked annotation source', async () => {
        setup();
        const trigger = screen.getByRole('button', {
            name: 'Move the selected annotations to another annotation source'
        });
        await waitFor(() => expect(trigger).toBeEnabled());
        await fireEvent.click(trigger);
        await fireEvent.click(await screen.findByRole('option', { name: 'predictions' }));
        await waitFor(() =>
            expect(moveAnnotations).toHaveBeenCalledWith({
                path: { collection_id: 'owner' },
                body: { annotation_ids: ids, target_annotation_collection_name: 'predictions' }
            })
        );
    });
});
