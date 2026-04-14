import { render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import VideoPlaybackDebugBadge from './VideoPlaybackDebugBadge.svelte';

describe('VideoPlaybackDebugBadge', () => {
    it('renders selected and rendered playback state', () => {
        render(VideoPlaybackDebugBadge, {
            props: {
                sample: {
                    clockTime: 10,
                    currentTime: 0.123,
                    mediaTime: 0.12,
                    sourceTime: 0.12,
                    selectedFrameNumber: 18,
                    selectedFrameTimestamp: 0.1,
                    windowStartTimestamp: 0.1,
                    windowEndTimestamp: 0.2,
                    nextFrameTimestamp: 0.2,
                    renderedFrameNumber: 18,
                    requestedFrameIndex: 17,
                    resolvedFrameIndex: 18,
                    pinnedFrameIndex: 17,
                    inFlightSeekTargetTime: 0.2,
                    selectorInvariantHolds: true,
                    source: 'rvfc',
                    strategy: 'midpoint',
                    selectionModeOverride: 'hybrid',
                    frameStartFrameNumber: 17,
                    midpointFrameNumber: 18
                }
            }
        });

        expect(screen.getByTestId('video-playback-debug')).toHaveTextContent('selected: 18');
        expect(screen.getByTestId('video-playback-debug')).toHaveTextContent('rendered: 18');
        expect(screen.getByTestId('video-playback-debug')).toHaveTextContent('mode: midpoint');
        expect(screen.getByTestId('video-playback-debug')).toHaveTextContent('override: hybrid');
        expect(screen.getByTestId('video-playback-debug')).toHaveTextContent('requested_idx: 17');
        expect(screen.getByTestId('video-playback-debug')).toHaveTextContent('resolved_idx: 18');
        expect(screen.getByTestId('video-playback-debug')).toHaveTextContent('pinned_frame: 17');
        expect(screen.getByTestId('video-playback-debug')).toHaveTextContent('invariant: ok');
    });
});
