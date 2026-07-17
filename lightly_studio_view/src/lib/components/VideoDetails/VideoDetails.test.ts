import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render } from '@testing-library/svelte';
import { flushSync } from 'svelte';
import { writable, type Writable } from 'svelte/store';
import type { FrameView, VideoView } from '$lib/api/lightly_studio_local';
import { useVideoFrames } from '$lib/hooks/useVideoFrames/useVideoFrames';
import { capturedProps, resetCapturedProps } from './VideoDetails.stub.svelte';

// VideoDetails wires many heavy children together; stub them all so the test
// exercises only the frame-loading and deep-link handoff logic it owns.
vi.mock('$lib/components', async () => {
    const stub = (await import('./VideoDetails.stub.svelte')).default;
    return {
        Card: stub,
        CardContent: stub,
        MetadataSegment: stub,
        SegmentTags: stub,
        VideoDetailsNavigation: stub,
        VideoFrameDetails: stub,
        VideoPlayer: stub
    };
});
vi.mock('../VideoSampleMetadata/VideoSampleMetadata.svelte', async () => ({
    default: (await import('./VideoDetails.stub.svelte')).default
}));
vi.mock(
    '../SampleDetails/SampleDetailsCaptionsSegment/SampleDetailsCaptionSegment.svelte',
    async () => ({
        default: (await import('./VideoDetails.stub.svelte')).default
    })
);
vi.mock('../VideoFrameAnnotationItem/VideoFrameAnnotationItem.svelte', async () => ({
    default: (await import('./VideoDetails.stub.svelte')).default
}));

// The resolved media URL is irrelevant here; avoid the env dependency it needs.
vi.mock('$lib/utils', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/utils')>()),
    getVideoURLById: () => 'http://mock-url.com/video.mp4'
}));

vi.mock('$lib/hooks/useVideoFrames/useVideoFrames', () => ({ useVideoFrames: vi.fn() }));
vi.mock('$lib/hooks/useVideoFrameAnnotations/useVideoFrameAnnotations', () => ({
    useVideoFrameAnnotations: vi.fn(() => new Map())
}));
// Event editing/adding needs a QueryClient; stub the annotation hooks so the
// test runs without a QueryClientProvider.
vi.mock('$lib/hooks/useUpdateAnnotationsMutation/useUpdateAnnotationsMutation', () => ({
    useUpdateAnnotationsMutation: vi.fn(() => ({ updateAnnotations: vi.fn() }))
}));
vi.mock('$lib/hooks/useCreateAnnotation/useCreateAnnotation', () => ({
    useCreateAnnotation: vi.fn(() => ({ createAnnotation: vi.fn() }))
}));
vi.mock('$lib/hooks/useCreateLabel/useCreateLabel', () => ({
    useCreateLabel: vi.fn(() => ({ createLabel: vi.fn() }))
}));
vi.mock('$lib/hooks/useAnnotationLabels/useAnnotationLabels', () => ({
    useAnnotationLabels: vi.fn(() => ({ data: [] }))
}));

import VideoDetails from './VideoDetails.svelte';

const FPS = 30;

const video = {
    sample_id: 'video-1',
    width: 1920,
    height: 1080,
    fps: FPS,
    sample: { sample_id: 'sample-1', tags: [], captions: [], metadata_dict: {} }
} as unknown as VideoView;

let currentFrame: Writable<FrameView | undefined>;
let loadFrameByPlaybackTime: ReturnType<typeof vi.fn>;
let loadFramesFromFrameNumber: ReturnType<typeof vi.fn>;

/** The most recent `startTimeS` VideoDetails handed to the VideoPlayer stub. */
function lastStartTimeS(): unknown {
    return capturedProps.filter((props) => 'startTimeS' in props).at(-1)?.startTimeS;
}

function renderDetails(frameNumber?: number) {
    return render(VideoDetails, {
        props: { video, datasetId: 'dataset-1', onVideoUpdate: vi.fn(), frameNumber }
    });
}

describe('VideoDetails', () => {
    beforeEach(() => {
        resetCapturedProps();
        currentFrame = writable<FrameView | undefined>(undefined);
        loadFrameByPlaybackTime = vi.fn().mockResolvedValue(undefined);
        loadFramesFromFrameNumber = vi.fn().mockResolvedValue(undefined);
        vi.mocked(useVideoFrames).mockReturnValue({
            currentFrame,
            frames: writable<FrameView[]>([]),
            playbackTime: writable(0),
            loading: false,
            reachedEnd: false,
            loadFrameByPlaybackTime,
            loadFramesFromFrameNumber,
            loadFrames: vi.fn()
        } as unknown as ReturnType<typeof useVideoFrames>);
    });

    it('loads the first frame by playback time when no frame is deep-linked', () => {
        renderDetails(undefined);
        flushSync();

        expect(loadFrameByPlaybackTime).toHaveBeenCalledWith(0, FPS);
        expect(loadFramesFromFrameNumber).not.toHaveBeenCalled();
        // Without a deep link, playback starts at the beginning.
        expect(lastStartTimeS()).toBe(0);
    });

    it('seeks to the deep-linked frame number on mount', () => {
        renderDetails(42);
        flushSync();

        expect(loadFramesFromFrameNumber).toHaveBeenCalledWith(42);
        expect(loadFrameByPlaybackTime).not.toHaveBeenCalled();
        // Start time waits (null) until the deep-linked frame resolves.
        expect(lastStartTimeS()).toBeNull();
    });

    it('hands the deep-linked frame timestamp to the player once it resolves', () => {
        renderDetails(42);
        flushSync();
        expect(lastStartTimeS()).toBeNull();

        // The matching frame arrives; its timestamp (+2ms nudge) becomes the start.
        flushSync(() =>
            currentFrame.set({
                frame_number: 42,
                frame_timestamp_s: 1,
                sample: {}
            } as unknown as FrameView)
        );

        expect(lastStartTimeS()).toBe(1.002);
    });

    it('ignores frames that do not match the deep-linked frame number', () => {
        renderDetails(42);
        flushSync();

        flushSync(() =>
            currentFrame.set({
                frame_number: 7,
                frame_timestamp_s: 3,
                sample: {}
            } as unknown as FrameView)
        );

        // A non-matching frame must not resolve the start time.
        expect(lastStartTimeS()).toBeNull();
    });
});
