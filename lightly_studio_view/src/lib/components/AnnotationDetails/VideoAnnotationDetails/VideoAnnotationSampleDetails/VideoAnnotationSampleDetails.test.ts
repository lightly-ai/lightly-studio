import { render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import VideoAnnotationSampleDetails from './VideoAnnotationSampleDetails.svelte';

const defaultProps = {
    datasetId: 'dataset-1',
    video: {
        sample_id: 'video-1',
        file_name: 'clip.mp4',
        file_path_abs: '/data/videos/clip.mp4',
        width: 640,
        height: 480,
        first_frame_sample_id: 'frame-1',
        sample: { sample_id: 'video-1', collection_id: 'video-collection-1', tags: [] }
    }
};

describe('VideoAnnotationSampleDetails', () => {
    it('shows the video file and links to the video details page', () => {
        render(VideoAnnotationSampleDetails, { props: defaultProps });

        expect(screen.getByText('clip.mp4')).toBeInTheDocument();
        expect(screen.getByText('/data/videos/clip.mp4')).toBeInTheDocument();
        expect(screen.getByRole('link', { name: 'View sample' })).toHaveAttribute(
            'href',
            expect.stringContaining('/datasets/dataset-1/video/video-collection-1/videos/video-1')
        );
    });
});
