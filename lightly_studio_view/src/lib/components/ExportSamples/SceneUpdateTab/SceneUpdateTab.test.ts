import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import SceneUpdateTab from './SceneUpdateTab.svelte';

const mocks = vi.hoisted(() => ({
    exportCollectionSceneUpdatePrepare: vi.fn(),
    exportCollectionSceneUpdateWrite: vi.fn(),
    triggerDownload: vi.fn(),
    createQuery: vi.fn()
}));

vi.mock('$lib/api/lightly_studio_local', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/api/lightly_studio_local')>()),
    exportCollectionSceneUpdatePrepare: mocks.exportCollectionSceneUpdatePrepare,
    exportCollectionSceneUpdateWrite: mocks.exportCollectionSceneUpdateWrite
}));
vi.mock('$lib/api/lightly_studio_local/@tanstack/svelte-query.gen', async (importOriginal) => ({
    ...(await importOriginal<
        typeof import('$lib/api/lightly_studio_local/@tanstack/svelte-query.gen')
    >()),
    exportCollectionSceneUpdateOptionsOptions: (options: unknown) => ({
        queryKey: ['scene-update-options', options]
    })
}));
vi.mock('@tanstack/svelte-query', async (importOriginal) => ({
    ...(await importOriginal<typeof import('@tanstack/svelte-query')>()),
    createQuery: mocks.createQuery
}));
vi.mock('../useExportDownload', async (importOriginal) => {
    const actual = await importOriginal<typeof import('../useExportDownload')>();
    return { ...actual, triggerDownload: mocks.triggerDownload };
});

const defaultOptions = {
    sequence_count: 1,
    annotation_collections: [
        { collection_id: 'pred-id', name: 'predictions', frame_ids: ['map', 'base_link'] },
        { collection_id: 'gt-id', name: 'ground_truth', frame_ids: ['odom', 'base_link'] }
    ],
    topic: '/perception/detections_3d',
    suffix: '_labeled'
};
const defaultProps = { collectionId: 'c1', scope: { sequence_id: 's1' } };

describe('SceneUpdateTab', () => {
    beforeEach(() => {
        vi.resetAllMocks();
        mocks.createQuery.mockReturnValue({ data: defaultOptions });
    });

    it('defaults to ground_truth, the first frame, and the default topic and suffix', async () => {
        mocks.exportCollectionSceneUpdatePrepare.mockResolvedValue({
            data: { export_key: 'key-1' }
        });
        render(SceneUpdateTab, { props: defaultProps });
        await fireEvent.click(screen.getByTestId('scene-update-download-button'));
        await waitFor(() => {
            expect(mocks.exportCollectionSceneUpdatePrepare).toHaveBeenCalledWith({
                path: { collection_id: 'c1' },
                body: {
                    sequence_id: 's1',
                    annotation_collection_id: 'gt-id',
                    target_frame_id: 'odom',
                    topic: '/perception/detections_3d',
                    suffix: '_labeled'
                }
            });
        });
    });

    it('defaults to the first frame of the selected source', async () => {
        mocks.createQuery.mockReturnValue({
            data: {
                ...defaultOptions,
                annotation_collections: [
                    {
                        collection_id: 'pred-id',
                        name: 'predictions',
                        frame_ids: ['map', 'base_link']
                    }
                ]
            }
        });
        mocks.exportCollectionSceneUpdatePrepare.mockResolvedValue({
            data: { export_key: 'key-1' }
        });
        render(SceneUpdateTab, { props: defaultProps });
        await fireEvent.click(screen.getByTestId('scene-update-download-button'));
        await waitFor(() => {
            expect(mocks.exportCollectionSceneUpdatePrepare).toHaveBeenCalledWith({
                path: { collection_id: 'c1' },
                body: expect.objectContaining({
                    annotation_collection_id: 'pred-id',
                    target_frame_id: 'map'
                })
            });
        });
    });

    it('download sends the edited topic and suffix', async () => {
        mocks.exportCollectionSceneUpdatePrepare.mockResolvedValue({
            data: { export_key: 'key-1' }
        });
        render(SceneUpdateTab, { props: defaultProps });
        await fireEvent.input(screen.getByTestId('scene-update-topic-input'), {
            target: { value: '/custom/cuboids' }
        });
        await fireEvent.input(screen.getByTestId('scene-update-suffix-input'), {
            target: { value: '_custom' }
        });
        await fireEvent.click(screen.getByTestId('scene-update-download-button'));
        await waitFor(() => {
            expect(mocks.exportCollectionSceneUpdatePrepare).toHaveBeenCalledWith({
                path: { collection_id: 'c1' },
                body: expect.objectContaining({ topic: '/custom/cuboids', suffix: '_custom' })
            });
        });
    });

    it('invalid suffix or empty topic disables the download', async () => {
        render(SceneUpdateTab, { props: defaultProps });
        const button = screen.getByTestId('scene-update-download-button');
        await fireEvent.input(screen.getByTestId('scene-update-suffix-input'), {
            target: { value: '_x/y' }
        });
        expect(button).toBeDisabled();
        await fireEvent.input(screen.getByTestId('scene-update-suffix-input'), {
            target: { value: '_x' }
        });
        await fireEvent.input(screen.getByTestId('scene-update-topic-input'), {
            target: { value: '' }
        });
        expect(button).toBeDisabled();
    });

    it('download sends the sequence scope and triggers the download URL', async () => {
        mocks.exportCollectionSceneUpdatePrepare.mockResolvedValue({
            data: { export_key: 'key-1' }
        });
        render(SceneUpdateTab, { props: defaultProps });
        await fireEvent.click(screen.getByTestId('scene-update-download-button'));
        await waitFor(() => {
            expect(mocks.triggerDownload).toHaveBeenCalledWith(
                expect.stringMatching(/\/export\/download\/key-1$/)
            );
        });
    });

    it('shows the download by default and the s3 write in the cloud tab', async () => {
        render(SceneUpdateTab, { props: defaultProps });
        expect(screen.getByTestId('scene-update-download-button')).toBeVisible();
        expect(screen.getByTestId('scene-update-write-button')).not.toBeVisible();
        await fireEvent.click(screen.getByTestId('scene-update-cloud-tab'));
        expect(screen.getByTestId('scene-update-download-button')).not.toBeVisible();
        expect(screen.getByTestId('scene-update-write-button')).toBeVisible();
    });

    it('write sends the shared export fields with the s3 bucket', async () => {
        mocks.exportCollectionSceneUpdateWrite.mockResolvedValue({
            data: { uris: ['s3://b/p/x_labeled.mcap'] }
        });
        render(SceneUpdateTab, { props: defaultProps });
        await fireEvent.click(screen.getByTestId('scene-update-cloud-tab'));
        await fireEvent.input(screen.getByPlaceholderText('s3://bucket'), {
            target: { value: 's3://b/p' }
        });
        await fireEvent.click(screen.getByTestId('scene-update-write-button'));
        await waitFor(() => {
            expect(mocks.exportCollectionSceneUpdateWrite).toHaveBeenCalledWith({
                path: { collection_id: 'c1' },
                body: {
                    sequence_id: 's1',
                    annotation_collection_id: 'gt-id',
                    target_frame_id: 'odom',
                    topic: '/perception/detections_3d',
                    suffix: '_labeled',
                    output_uri: 's3://b/p'
                }
            });
        });
    });

    it('no shared frame disables both actions', async () => {
        mocks.createQuery.mockReturnValue({
            data: {
                ...defaultOptions,
                annotation_collections: [
                    { collection_id: 'gt-id', name: 'ground_truth', frame_ids: [] }
                ]
            }
        });
        render(SceneUpdateTab, { props: defaultProps });
        await fireEvent.click(screen.getByTestId('scene-update-cloud-tab'));
        await fireEvent.input(screen.getByPlaceholderText('s3://bucket'), {
            target: { value: 's3://b/p' }
        });
        expect(
            screen.getByText('The selected recordings share no coordinate frame.')
        ).toBeInTheDocument();
        expect(screen.getByTestId('scene-update-download-button')).toBeDisabled();
        expect(screen.getByTestId('scene-update-write-button')).toBeDisabled();
    });

    it('no matching sequences shows the filter message', () => {
        mocks.createQuery.mockReturnValue({
            data: {
                ...defaultOptions,
                sequence_count: 0,
                annotation_collections: [
                    { collection_id: 'gt-id', name: 'ground_truth', frame_ids: [] }
                ]
            }
        });
        render(SceneUpdateTab, { props: defaultProps });
        expect(screen.getByText('No sequences match the current filters.')).toBeInTheDocument();
        expect(
            screen.queryByText('The selected recordings share no coordinate frame.')
        ).not.toBeInTheDocument();
        expect(screen.getByTestId('scene-update-download-button')).toBeDisabled();
    });
});
