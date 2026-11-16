import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import SceneUpdateS3Write from './SceneUpdateS3Write.svelte';

const mocks = vi.hoisted(() => ({
    exportCollectionSceneUpdateWrite: vi.fn()
}));

vi.mock('$lib/api/lightly_studio_local', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/api/lightly_studio_local')>()),
    exportCollectionSceneUpdateWrite: mocks.exportCollectionSceneUpdateWrite
}));

const requestBody = {
    sequence_id: 's1',
    annotation_collection_id: 'gt-id',
    target_frame_id: 'odom',
    topic: '/perception/detections_3d',
    suffix: '_labeled'
};
const defaultProps = { collectionId: 'c1', canExport: true, requestBody: () => requestBody };

describe('SceneUpdateS3Write', () => {
    beforeEach(() => {
        vi.resetAllMocks();
    });

    it('write is disabled until an s3 bucket is entered', async () => {
        render(SceneUpdateS3Write, { props: defaultProps });
        const button = screen.getByTestId('scene-update-write-button');
        const input = screen.getByPlaceholderText('s3://bucket');
        expect(button).toBeDisabled();
        await fireEvent.input(input, { target: { value: 's3://' } });
        expect(button).toBeDisabled();
        await fireEvent.input(input, { target: { value: 's3://b/p' } });
        expect(button).toBeEnabled();
    });

    it('write is disabled when the export fields are invalid', async () => {
        render(SceneUpdateS3Write, { props: { ...defaultProps, canExport: false } });
        await fireEvent.input(screen.getByPlaceholderText('s3://bucket'), {
            target: { value: 's3://b/p' }
        });
        expect(screen.getByTestId('scene-update-write-button')).toBeDisabled();
    });

    it('write sends the bucket and shows the written uris', async () => {
        mocks.exportCollectionSceneUpdateWrite.mockResolvedValue({
            data: { uris: ['s3://b/p/x_labeled.mcap'] }
        });
        render(SceneUpdateS3Write, { props: defaultProps });
        await fireEvent.input(screen.getByPlaceholderText('s3://bucket'), {
            target: { value: 's3://b/p' }
        });
        await fireEvent.click(screen.getByTestId('scene-update-write-button'));
        await waitFor(() => {
            expect(screen.getByText('s3://b/p/x_labeled.mcap')).toBeInTheDocument();
        });
        expect(mocks.exportCollectionSceneUpdateWrite).toHaveBeenCalledWith({
            path: { collection_id: 'c1' },
            body: { ...requestBody, output_uri: 's3://b/p' }
        });
    });

    it('write shows the error when the request fails', async () => {
        mocks.exportCollectionSceneUpdateWrite.mockResolvedValue({ error: 'exists' });
        render(SceneUpdateS3Write, { props: defaultProps });
        await fireEvent.input(screen.getByPlaceholderText('s3://bucket'), {
            target: { value: 's3://b/p' }
        });
        await fireEvent.click(screen.getByTestId('scene-update-write-button'));
        await waitFor(() => {
            expect(screen.getByText(/Export failed/)).toBeInTheDocument();
        });
    });
});
