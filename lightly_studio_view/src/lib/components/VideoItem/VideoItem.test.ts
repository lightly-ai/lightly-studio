import { render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import type { VideoView } from '$lib/api/lightly_studio_local';
import VideoItem from './VideoItem.svelte';

vi.mock('../Video/Video.svelte', async () => ({
    default: (await import('./Empty.mock.svelte')).default
}));
vi.mock('../VideoFrameAnnotationItem/VideoFrameAnnotationItem.svelte', async () => ({
    default: (await import('./Empty.mock.svelte')).default
}));
vi.mock('$lib/components/SampleClassificationPills/SampleClassificationPills.svelte', async () => ({
    default: (await import('./Empty.mock.svelte')).default
}));
vi.mock('$app/navigation', () => ({ goto: vi.fn() }));
vi.mock('$app/state', () => ({ page: { params: {} } }));

const baseVideo = {
    sample_id: 'video-1',
    width: 320,
    height: 240,
    frame: null,
    sample: { captions: [], annotations: [] }
} as unknown as VideoView;

describe('VideoItem', () => {
    it('shows the formatted order value on the tile', () => {
        render(VideoItem, { props: { video: { ...baseVideo, order_value: 0.75 }, size: 100 } });
        expect(screen.getByText('0.75')).toBeInTheDocument();
    });

    it('falls back to the similarity score when there is no order value', () => {
        render(VideoItem, {
            props: { video: { ...baseVideo, similarity_score: 0.884 }, size: 100 }
        });
        expect(screen.getByText('0.88')).toBeInTheDocument();
    });
});
