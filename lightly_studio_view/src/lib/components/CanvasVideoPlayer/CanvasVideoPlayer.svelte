<script lang="ts">
    import type { FrameView } from '$lib/api/lightly_studio_local';
    import type { SampleImageObjectFit } from '$lib/components/SampleImage/types';
    import { Button } from '$lib/components/ui';
    import { Slider } from '$lib/components/ui/slider';
    import { useHideAnnotations } from '$lib/hooks/useHideAnnotations';
    import { useSettings } from '$lib/hooks/useSettings';
    import {
        getFrameWindowTarget,
        selectPlaybackFrame,
        type PlaybackSelectionStrategy
    } from '$lib/utils/frame';
    import {
        createVideoPlaybackController,
        type PlaybackSample,
        type PlaybackSource
    } from '$lib/utils/videoPlaybackController';
    import {
        buildPlaybackAnnotationPayload,
        renderCanvasPlaybackFrame,
        type PlaybackAnnotationPayload
    } from './renderCanvasPlaybackFrame';

    type CanvasVideoPlayerProps = {
        src: string;
        frames: FrameView[];
        sampleWidth: number;
        sampleHeight: number;
        poster?: string | null;
        autoplay?: boolean;
        muted?: boolean;
        loop?: boolean;
        showControls?: boolean;
        showAnnotations?: boolean;
        lazyLoad?: boolean;
        objectFit?: SampleImageObjectFit;
        className?: string;
        initialFrameNumber?: number;
        onFrameChange?: (frame: FrameView | null) => void;
    };

    let {
        src,
        frames,
        sampleWidth,
        sampleHeight,
        poster = null,
        autoplay = false,
        muted = true,
        loop = false,
        showControls = false,
        showAnnotations = true,
        lazyLoad = false,
        objectFit = 'contain',
        className = '',
        initialFrameNumber,
        onFrameChange = () => {}
    }: CanvasVideoPlayerProps = $props();

    const { isHidden } = useHideAnnotations();
    const { showBoundingBoxesForSegmentationStore } = useSettings();

    let videoEl: HTMLVideoElement | null = $state(null);
    let canvasEl: HTMLCanvasElement | null = $state(null);
    let maskCanvasEl: HTMLCanvasElement | null = null;

    let resolvedFrameIndex = $state(0);
    let pinnedFrameIndex = $state<number | null>(null);
    let isPlaying = $state(false);
    let pendingHybridSeekPlaybackSamples = $state(0);
    let lastFrameChangeId: string | null = null;
    let lastPlaybackSample: PlaybackSample<FrameView> | null = null;
    let cachedPayloadKey: string | null = null;
    let cachedPayload: PlaybackAnnotationPayload = { masks: [], boxes: [] };
    let initialFrameApplied = false;
    let pendingSeekTargetTime: number | null = null;
    let inFlightSeekFrameIndex: number | null = null;
    let queuedSeekFrameIndex: number | null = null;
    let pendingPauseNormalization = $state(false);
    let lastActiveFrameIndex: number | null = $state(null);
    let hasStarted = $state(false);

    const clampFrameIndex = (value: number): number => {
        if (frames.length === 0) {
            return 0;
        }

        return Math.max(0, Math.min(value, frames.length - 1));
    };

    const initialFrameIndex = $derived.by(() => {
        if (initialFrameNumber == null) {
            return 0;
        }

        const index = frames.findIndex((frame) => frame.frame_number === initialFrameNumber);
        return index >= 0 ? index : 0;
    });

    const getFrameAtIndex = (frameIndex: number): FrameView | null => {
        return frames[clampFrameIndex(frameIndex)] ?? null;
    };

    const objectFitClass = $derived(objectFit === 'cover' ? 'object-cover' : 'object-contain');
    const displayedFrameIndex = $derived(pinnedFrameIndex ?? resolvedFrameIndex);
    const currentFrame = $derived(getFrameAtIndex(displayedFrameIndex));
    const currentFrameNumber = $derived(currentFrame?.frame_number ?? 0);

    function updateFrameChange(frame: FrameView | null) {
        const selectedFrameId = frame?.sample_id ?? null;
        if (selectedFrameId === lastFrameChangeId) {
            return;
        }

        lastFrameChangeId = selectedFrameId;
        onFrameChange(frame);
    }

    function getCachedPayload(frame: FrameView | null): PlaybackAnnotationPayload {
        if (!frame || $isHidden || !showAnnotations) {
            cachedPayloadKey = null;
            cachedPayload = { masks: [], boxes: [] };
            return cachedPayload;
        }

        const key = [
            frame.sample_id,
            $showBoundingBoxesForSegmentationStore ? '1' : '0',
            showAnnotations ? '1' : '0'
        ].join(':');

        if (cachedPayloadKey === key) {
            return cachedPayload;
        }

        cachedPayload = buildPlaybackAnnotationPayload({
            frame,
            showBoundingBoxesForSegmentation: $showBoundingBoxesForSegmentationStore
        });
        cachedPayloadKey = key;
        return cachedPayload;
    }

    function drawSample(sample: PlaybackSample<FrameView>) {
        if (!canvasEl || !videoEl || !maskCanvasEl) {
            return;
        }

        const canvasCtx = canvasEl.getContext('2d');
        const maskCtx = maskCanvasEl.getContext('2d');
        if (!canvasCtx || !maskCtx) {
            return;
        }

        const payload = getCachedPayload(sample.selection.frame as FrameView | null);
        const scaleX = canvasEl.clientWidth / sampleWidth || 1;
        const scaleY = canvasEl.clientHeight / sampleHeight || 1;

        renderCanvasPlaybackFrame({
            canvasCtx,
            maskCtx,
            maskCanvas: maskCanvasEl,
            mediaSource: videoEl,
            sampleWidth,
            sampleHeight,
            payload,
            scaleX,
            scaleY
        });

        if (videoEl.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA) {
            hasStarted = true;
        }
    }

    function buildPinnedPlaybackSample(
        sample: PlaybackSample<FrameView>,
        frameIndex: number
    ): PlaybackSample<FrameView> {
        const frameWindowTarget = getFrameWindowTarget({
            frames,
            frameIndex,
            videoDuration: videoEl?.duration
        });

        if (!frameWindowTarget) {
            return sample;
        }

        return {
            ...sample,
            selection: {
                frame: frameWindowTarget.frame,
                index: frameWindowTarget.index,
                selectedTimestamp: frameWindowTarget.selectedTimestamp,
                windowStartTimestamp: frameWindowTarget.windowStartTimestamp,
                windowEndTimestamp: frameWindowTarget.windowEndTimestamp,
                nextTimestamp: frames[frameWindowTarget.index + 1]?.frame_timestamp_s ?? null,
                selectorInvariantHolds:
                    frameWindowTarget.windowStartTimestamp <= sample.selection.sourceTime &&
                    sample.selection.sourceTime < frameWindowTarget.windowEndTimestamp,
                sourceTime: sample.selection.sourceTime,
                strategy: 'frame_start'
            }
        };
    }

    function resolveAutomaticSelectionStrategy(source: PlaybackSource): PlaybackSelectionStrategy {
        if (source === 'event' || !isPlaying || pendingHybridSeekPlaybackSamples > 0) {
            return 'frame_start';
        }

        return 'midpoint';
    }

    function handlePlaybackSample(sample: PlaybackSample<FrameView>) {
        if (pendingPauseNormalization && sample.source === 'event') {
            return;
        }

        if (isPlaying && sample.selection.index != null) {
            lastActiveFrameIndex = sample.selection.index;
        }

        if (
            pendingSeekTargetTime != null &&
            sample.source === 'event' &&
            Math.abs(sample.currentTime - pendingSeekTargetTime) > 0.0005
        ) {
            return;
        }

        const nextResolvedFrameIndex = sample.selection.index ?? 0;
        const resolvedPendingSeek =
            pendingSeekTargetTime != null &&
            Math.abs(sample.selection.sourceTime - pendingSeekTargetTime) <= 0.0005;

        resolvedFrameIndex = nextResolvedFrameIndex;

        if (resolvedPendingSeek && queuedSeekFrameIndex != null) {
            pendingSeekTargetTime = null;
            inFlightSeekFrameIndex = null;
            const nextQueuedFrameIndex = queuedSeekFrameIndex;
            queuedSeekFrameIndex = null;
            issueSeek(nextQueuedFrameIndex);
            return;
        }

        let sampleToRender = sample;
        if (!isPlaying && pinnedFrameIndex != null) {
            sampleToRender = buildPinnedPlaybackSample(sample, pinnedFrameIndex);
        }

        lastPlaybackSample = sampleToRender;
        drawSample(sampleToRender);

        if (resolvedPendingSeek) {
            pendingSeekTargetTime = null;
            inFlightSeekFrameIndex = null;
        }

        if (sample.source !== 'event' && pendingHybridSeekPlaybackSamples > 0) {
            pendingHybridSeekPlaybackSamples -= 1;
        }

        updateFrameChange(sampleToRender.selection.frame as FrameView | null);
    }

    function handleLoadedMetadata() {
        if (!videoEl || !frames.length) {
            return;
        }

        if (!initialFrameApplied) {
            const initialFrame = getFrameAtIndex(initialFrameIndex);
            const initialTime = initialFrame?.frame_timestamp_s ?? 0;

            videoEl.currentTime = initialTime;
            resolvedFrameIndex = clampFrameIndex(initialFrameIndex);
            initialFrameApplied = true;
        }

        if (autoplay) {
            void videoEl.play().catch(() => {});
        }
    }

    async function togglePlayback() {
        if (!videoEl) {
            return;
        }

        if (videoEl.paused || videoEl.ended) {
            await videoEl.play().catch(() => {});
            return;
        }

        pendingPauseNormalization = true;
        videoEl.pause();
    }

    function issueSeek(nextFrameIndex: number) {
        const nextFrame = getFrameAtIndex(nextFrameIndex);
        if (!nextFrame || !videoEl) {
            return;
        }

        const pausedSeekTarget = !isPlaying
            ? getFrameWindowTarget({
                  frames,
                  frameIndex: nextFrameIndex,
                  videoDuration: videoEl.duration
              })
            : null;

        inFlightSeekFrameIndex = nextFrameIndex;
        pendingHybridSeekPlaybackSamples = 1;
        pendingSeekTargetTime = pausedSeekTarget?.seekTargetTime ?? nextFrame.frame_timestamp_s;
        videoEl.currentTime = pendingSeekTargetTime;
    }

    function requestSeek(nextFrameIndex: number) {
        const clampedFrameIndex = clampFrameIndex(nextFrameIndex);
        if (!isPlaying) {
            pinnedFrameIndex = clampedFrameIndex;
            updateFrameChange(getFrameAtIndex(clampedFrameIndex));
        }

        if (inFlightSeekFrameIndex != null) {
            queuedSeekFrameIndex = clampedFrameIndex;
            return;
        }

        if (isPlaying && clampedFrameIndex === resolvedFrameIndex) {
            queuedSeekFrameIndex = null;
            return;
        }

        queuedSeekFrameIndex = null;
        issueSeek(clampedFrameIndex);
    }

    function handleSeekChange(nextValues: number[]) {
        const [nextValue = 0] = nextValues;
        requestSeek(Math.round(nextValue));
    }

    $effect(() => {
        if (!videoEl || !canvasEl || frames.length === 0) {
            return;
        }

        if (!maskCanvasEl) {
            maskCanvasEl = document.createElement('canvas');
        }

        canvasEl.width = sampleWidth;
        canvasEl.height = sampleHeight;
        maskCanvasEl.width = sampleWidth;
        maskCanvasEl.height = sampleHeight;

        const controller = createVideoPlaybackController({
            videoEl,
            frames,
            emitDuplicateFrames: true,
            selectionStrategy: ({ source }) => resolveAutomaticSelectionStrategy(source),
            onSample: handlePlaybackSample
        });

        controller.syncImmediately();

        return () => controller.destroy();
    });

    $effect(() => {
        if (!videoEl) {
            return;
        }

        const target = videoEl;

        const handlePlay = () => {
            isPlaying = true;
            pinnedFrameIndex = null;
            queuedSeekFrameIndex = null;
            pendingPauseNormalization = false;
        };
        const handlePause = () => {
            isPlaying = false;
            pendingHybridSeekPlaybackSamples = 0;

            if (pendingPauseNormalization) {
                const pauseSelection = selectPlaybackFrame({
                    frames,
                    sourceTime: target.currentTime,
                    strategy: 'midpoint'
                });
                const pauseFrameIndex =
                    lastActiveFrameIndex ?? pauseSelection.index ?? resolvedFrameIndex;
                pendingPauseNormalization = false;
                requestSeek(pauseFrameIndex);
            }

            pendingPauseNormalization = false;
        };
        const handleEnded = () => {
            isPlaying = false;
            pendingHybridSeekPlaybackSamples = 0;
            pendingPauseNormalization = false;
        };

        target.addEventListener('play', handlePlay);
        target.addEventListener('pause', handlePause);
        target.addEventListener('ended', handleEnded);

        return () => {
            target.removeEventListener('play', handlePlay);
            target.removeEventListener('pause', handlePause);
            target.removeEventListener('ended', handleEnded);
        };
    });

    $effect(() => {
        void $isHidden;
        void $showBoundingBoxesForSegmentationStore;
        void showAnnotations;

        cachedPayloadKey = null;
        if (lastPlaybackSample) {
            drawSample(lastPlaybackSample);
        }
    });
</script>

<div
    class={`relative flex min-h-0 flex-1 flex-col overflow-hidden rounded-lg bg-black ${className}`}
>
    <video
        bind:this={videoEl}
        class="pointer-events-none absolute left-0 top-0 h-px w-px opacity-0"
        {src}
        {muted}
        playsinline
        preload={lazyLoad ? 'metadata' : 'auto'}
        {loop}
        aria-hidden="true"
        tabindex="-1"
        onloadedmetadata={handleLoadedMetadata}
    ></video>

    <div class="relative flex min-h-0 flex-1 items-center justify-center bg-black">
        <canvas
            bind:this={canvasEl}
            class={`block h-full w-full ${objectFitClass}`}
            data-testid="canvas-video-player"
        ></canvas>
        {#if poster && !hasStarted}
            <img
                src={poster}
                alt=""
                class={`pointer-events-none absolute inset-0 h-full w-full ${objectFitClass}`}
            />
        {/if}
    </div>

    {#if showControls}
        <div
            class="flex items-center gap-3 border-t border-white/10 bg-black px-3 py-2 text-sm text-white"
        >
            <Button type="button" variant="secondary" onclick={togglePlayback}>
                {isPlaying ? 'Pause' : 'Play'}
            </Button>
            <Slider
                type="multiple"
                min={0}
                max={Math.max(frames.length - 1, 0)}
                step={1}
                value={[displayedFrameIndex]}
                class="flex-1"
                onValueChange={handleSeekChange}
            />
            <div class="min-w-28 text-right text-xs">
                Frame {currentFrameNumber}
            </div>
        </div>
    {/if}
</div>
