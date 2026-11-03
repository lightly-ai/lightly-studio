import { QueryClient } from '@tanstack/svelte-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { toast } from 'svelte-sonner';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
    bulkCreateClassifications,
    bulkDeleteAnnotations,
    countImageAnnotationsByCollection,
    deleteForSamples,
    readAnnotationCollections,
    readAnnotationLabels
} from '$lib/api/lightly_studio_local/sdk.gen';
import { useAnnotationCollectionsFilter, useGlobalStorage } from '$lib/hooks';
import ImagesAnnotatePopoverHarness from './ImagesAnnotatePopoverHarness.svelte';

const mocks = vi.hoisted(() => ({
    target: { kind: 'ids', ids: ['s1'] } as unknown
}));

vi.mock('$lib/api/lightly_studio_local/sdk.gen', async () => ({
    ...(await vi.importActual('$lib/api/lightly_studio_local/sdk.gen')),
    readAnnotationCollections: vi.fn(),
    readAnnotationLabels: vi.fn(),
    countImageAnnotationsByCollection: vi.fn(),
    bulkCreateClassifications: vi.fn(),
    bulkCreateClassificationsByFilter: vi.fn(),
    bulkDeleteAnnotations: vi.fn(),
    deleteForSamples: vi.fn(),
    getAnalyticsConfig: vi.fn().mockResolvedValue({})
}));
vi.mock('svelte-sonner', () => ({
    toast: { success: vi.fn(), error: vi.fn(), dismiss: vi.fn() }
}));
vi.mock('$app/state', () => ({ page: { params: { dataset_id: 'root' } } }));
vi.mock('$lib/hooks/useSelectionTarget/useSelectionTarget', () => ({
    getSelectionTarget: () => mocks.target
}));

const gt = { collection_id: 'src-gt', name: 'ground_truth' };
const pred = { collection_id: 'src-pred', name: 'predictions' };

function mockSources(sources: { collection_id: string; name: string }[]) {
    vi.mocked(readAnnotationCollections).mockResolvedValue({ data: sources } as never);
    const filter = useAnnotationCollectionsFilter();
    filter.setCollectionIdToName(Object.fromEntries(sources.map((s) => [s.collection_id, s.name])));
    filter.setSelectedCollectionIds(sources.map((s) => s.collection_id));
}

function setup() {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const invalidate = vi.spyOn(client, 'invalidateQueries');
    render(ImagesAnnotatePopoverHarness, { client, selectedCount: 1 });
    return { invalidate };
}

async function pickSource(name: string) {
    const trigger = await screen.findByRole('button', { name: 'Annotation source' });
    await waitFor(() => expect(trigger).toBeEnabled());
    await fireEvent.click(trigger);
    await fireEvent.click(await screen.findByRole('option', { name }));
}

const stored = new Map<string, string>();
const SOURCE_KEY = 'lightly-studio.pill-annotate-source.c1';

afterEach(() => vi.unstubAllGlobals());

beforeEach(() => {
    vi.clearAllMocks();
    stored.clear();
    vi.stubGlobal('localStorage', {
        getItem: (key: string) => stored.get(key) ?? null,
        setItem: (key: string, value: string) => stored.set(key, value),
        removeItem: (key: string) => stored.delete(key)
    });
    mocks.target = { kind: 'ids', ids: ['s1'] };
    const storage = useGlobalStorage();
    storage.clearSelectedSamples('c1');
    storage.toggleSampleSelection('s1', 'c1');
    mockSources([gt]);
    vi.mocked(readAnnotationLabels).mockResolvedValue({
        data: [
            { annotation_label_id: 'l-raccoon', annotation_label_name: 'raccoon', dataset_id: 'd' },
            { annotation_label_id: 'l-fox', annotation_label_name: 'fox', dataset_id: 'd' }
        ]
    } as never);
    vi.mocked(countImageAnnotationsByCollection).mockResolvedValue({
        data: [
            { label_name: 'raccoon', current_count: 1, total_count: 4 },
            { label_name: 'fox', current_count: 0, total_count: 2 }
        ]
    } as never);
    vi.mocked(bulkCreateClassifications).mockResolvedValue({
        data: { created_annotation_ids: ['a'], created_count: 1, skipped_count: 0 }
    } as never);
    vi.mocked(deleteForSamples).mockResolvedValue({ data: { deleted_count: 1 } } as never);
});

describe('ImagesAnnotatePopover', () => {
    it('has no source picked when there are several sources, and + is refused', async () => {
        mockSources([gt, pred]);
        setup();
        expect(await screen.findByRole('button', { name: 'Annotation source' })).toHaveTextContent(
            'Choose source'
        );
        await fireEvent.click(await screen.findByLabelText('Add fox to selection'));
        expect(toast.error).toHaveBeenCalledWith(expect.stringContaining('Pick a source'));
        expect(bulkCreateClassifications).not.toHaveBeenCalled();
    });

    it('preselects the remembered source and remembers a new pick', async () => {
        stored.set(SOURCE_KEY, 'predictions');
        mockSources([gt, pred]);
        setup();
        const trigger = await screen.findByRole('button', { name: 'Annotation source' });
        await waitFor(() => expect(trigger).toHaveTextContent('predictions'));

        await pickSource('ground_truth');

        expect(stored.get(SOURCE_KEY)).toBe('ground_truth');
        expect(trigger).toHaveTextContent('ground_truth');
    });

    it('asks to choose when the remembered source is hidden', async () => {
        stored.set(SOURCE_KEY, 'predictions');
        mockSources([gt, pred]);
        useAnnotationCollectionsFilter().setSelectedCollectionIds(['src-gt']);
        setup();
        expect(await screen.findByRole('button', { name: 'Annotation source' })).toHaveTextContent(
            'Choose source'
        );
    });

    it('number keys add the first classes while the search is empty', async () => {
        setup();
        const input = await screen.findByPlaceholderText('Search or create a class…');
        await screen.findByText('0/1');
        expect(screen.getByText('2')).toBeInTheDocument();

        await fireEvent.keyDown(input, { key: '2' });

        await waitFor(() =>
            expect(bulkCreateClassifications).toHaveBeenCalledWith(
                expect.objectContaining({ body: expect.objectContaining({ class_name: 'fox' }) })
            )
        );
    });

    it('digits go to a search that is not empty', async () => {
        setup();
        const user = userEvent.setup();
        const input = await screen.findByPlaceholderText('Search or create a class…');
        await screen.findByText('0/1');

        await user.type(input, 'f2');

        expect(input).toHaveValue('f2');
        expect(bulkCreateClassifications).not.toHaveBeenCalled();
    });

    it('cannot pick a hidden source', async () => {
        mockSources([gt, pred]);
        useAnnotationCollectionsFilter().setSelectedCollectionIds(['src-gt']);
        setup();
        await pickSource('predictions');
        expect(toast.error).toHaveBeenCalledWith(
            'predictions is hidden. Show it in the Annotations panel to add annotations to it.'
        );
        expect(screen.getByRole('button', { name: 'Annotation source' })).toHaveTextContent(
            'Choose source'
        );
    });

    it('shows k/N counts restricted to the picked source', async () => {
        setup();
        expect(await screen.findByText('1/1')).toBeInTheDocument();
        expect(screen.getByText('0/1')).toBeInTheDocument();
        expect(countImageAnnotationsByCollection).toHaveBeenCalledWith(
            expect.objectContaining({
                body: {
                    filter: {
                        sample_filter: {
                            sample_ids: ['s1'],
                            annotations_filter: { collection_ids: ['src-gt'] }
                        }
                    },
                    annotation_type: 'classification',
                    count_mode: 'samples'
                }
            })
        );
    });

    it('+ bulk creates the class in the source and refreshes counts and grid', async () => {
        const { invalidate } = setup();
        await screen.findByText('0/1');
        await fireEvent.click(screen.getByLabelText('Add fox to selection'));
        await waitFor(() =>
            expect(bulkCreateClassifications).toHaveBeenCalledWith({
                path: { collection_id: 'c1' },
                body: {
                    class_name: 'fox',
                    annotation_collection_name: 'ground_truth',
                    sample_ids: ['s1']
                }
            })
        );
        const keys = invalidate.mock.calls.map(([filters]) => JSON.stringify(filters?.queryKey));
        expect(keys.some((k) => k.includes('countImageAnnotationsByCollection'))).toBe(true);
        expect(keys).toContain(JSON.stringify(['readImagesInfinite', 'c1']));
    });

    it('Undo after + deletes exactly the created classifications', async () => {
        vi.mocked(bulkCreateClassifications).mockResolvedValue({
            data: { created_annotation_ids: ['a1'], created_count: 1, skipped_count: 0 }
        } as never);
        vi.mocked(bulkDeleteAnnotations).mockResolvedValue({ data: { deleted_count: 1 } } as never);
        setup();
        await screen.findByText('0/1');
        await fireEvent.click(screen.getByLabelText('Add fox to selection'));

        await waitFor(() =>
            expect(toast.success).toHaveBeenCalledWith(
                'Added the annotation class to 1 images.',
                expect.objectContaining({ action: expect.objectContaining({ label: 'Undo' }) })
            )
        );
        const [, options] = vi.mocked(toast.success).mock.calls[0] as unknown as [
            string,
            { action: { onClick: () => void } }
        ];
        options.action.onClick();

        await waitFor(() =>
            expect(bulkDeleteAnnotations).toHaveBeenCalledWith({
                path: { collection_id: 'c1' },
                body: { annotation_ids: ['a1'] }
            })
        );
        await waitFor(() => expect(toast.success).toHaveBeenCalledWith('Undone'));
    });

    it('offers Create for a new class name', async () => {
        setup();
        const user = userEvent.setup();
        await user.type(await screen.findByPlaceholderText('Search or create a class…'), 'deer');
        await user.click(await screen.findByText("Create 'deer'"));
        await waitFor(() =>
            expect(bulkCreateClassifications).toHaveBeenCalledWith(
                expect.objectContaining({
                    body: expect.objectContaining({ class_name: 'deer' })
                })
            )
        );
    });

    it('× asks to confirm; Cancel calls nothing and Delete calls delete_for_samples', async () => {
        const { invalidate } = setup();
        await screen.findByText('1/1');
        await fireEvent.click(screen.getByLabelText('Remove raccoon from selection'));
        expect(
            await screen.findByText('Delete raccoon from 1 image in ground_truth?')
        ).toBeInTheDocument();
        await fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
        expect(deleteForSamples).not.toHaveBeenCalled();

        await fireEvent.click(screen.getByLabelText('Remove raccoon from selection'));
        await fireEvent.click(await screen.findByRole('button', { name: 'Delete' }));
        await waitFor(() =>
            expect(deleteForSamples).toHaveBeenCalledWith({
                path: { collection_id: 'c1' },
                body: {
                    sample_ids: ['s1'],
                    annotation_label_id: 'l-raccoon',
                    annotation_collection_id: 'src-gt'
                }
            })
        );
        const keys = invalidate.mock.calls.map(([filters]) => JSON.stringify(filters?.queryKey));
        expect(keys.some((k) => k.includes('countImageAnnotationsByCollection'))).toBe(true);
        expect(keys).toContain(JSON.stringify(['readImagesInfinite', 'c1']));
    });
});
