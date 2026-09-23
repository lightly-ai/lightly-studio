import { render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import type { VideoFrameView } from '$lib/api/lightly_studio_local';
import VideoFrameAnnotationItem from './VideoFrameAnnotationItem.svelte';

vi.mock('..', async () => {
    const module = await import('./SampleAnnotations.mock.svelte');
    return { SampleAnnotations: module.default };
});

describe('VideoFrameAnnotationItem', () => {
    it('bounds annotation rendering to the video tile dimensions', () => {
        render(VideoFrameAnnotationItem, {
            props: {
                sample: {
                    sample_id: 'frame-1',
                    sample: { annotations: [] }
                } as unknown as VideoFrameView,
                width: 320,
                height: 180,
                sampleWidth: 1920,
                sampleHeight: 1080,
                sampleImageObjectFit: 'cover',
                showLabel: false
            }
        });

        expect(screen.getByTestId('mock-video-sample-annotations')).toHaveAttribute(
            'data-output-width',
            '320'
        );
        expect(screen.getByTestId('mock-video-sample-annotations')).toHaveAttribute(
            'data-output-height',
            '180'
        );
        expect(screen.getByTestId('mock-video-sample-annotations')).toHaveAttribute(
            'data-object-fit',
            'cover'
        );
    });
});
