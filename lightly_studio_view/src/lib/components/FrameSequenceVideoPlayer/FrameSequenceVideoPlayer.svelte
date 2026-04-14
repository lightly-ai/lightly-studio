<script lang="ts">
    import { onMount } from 'svelte';
    import type { FrameView } from '$lib/api/lightly_studio_local';
    import type { SampleImageObjectFit } from '$lib/components/SampleImage/types';
    import { Spinner } from '$lib/components';
    import { Slider } from '$lib/components/ui/slider';
    import { useCustomLabelColors } from '$lib/hooks/useCustomLabelColors';
    import { useHideAnnotations } from '$lib/hooks/useHideAnnotations';
    import { useSettings } from '$lib/hooks/useSettings';
    import type { PlaybackDebugSample } from '$lib/components/VideoPlaybackDebugBadge/VideoPlaybackDebugBadge.svelte';
    import VideoPlaybackDebugBadge from '$lib/components/VideoPlaybackDebugBadge/VideoPlaybackDebugBadge.svelte';
    import { getGridFrameURL } from '$lib/utils';
    import { getFrameWindowTarget, selectPlaybackFrame } from '$lib/utils/frame';
    import {
        buildPlaybackAnnotationPayload,
        renderCanvasPlaybackFrame,
        type PlaybackAnnotationPayload
    } from '$lib/components/CanvasVideoPlayer/renderCanvasPlaybackFrame';

    type FrameSequenceVideoPlayerProps = {
        frames: FrameView[];
        sampleWidth: number;
        sampleHeight: number;
        durationSeconds?: number | null;
        initialFrameIndex?: number;
        className?: string;
        objectFit?: SampleImageObjectFit;
        showControls?: boolean;
        showDebug?: boolean;
        showAnnotations?: boolean;
        testDiagnosticsId?: string;
        resolveFrameImageUrl?: (frame: FrameView, index: number) => string;
    };

    let {
        frames,
        sampleWidth,
        sampleHeight,
        durationSeconds = null,
        initialFrameIndex = 0,
        className = '',
        objectFit = 'contain',
        showControls = true,
        showDebug = false,
        showAnnotations = true,
        testDiagnosticsId,
        resolveFrameImageUrl
    }: FrameSequenceVideoPlayerProps = $props();

    const { customLabelColorsStore, colorVersion } = useCustomLabelColors();
    const { isHidden } = useHideAnnotations();
    const { showBoundingBoxesForSegmentationStore } = useSettings();

    let canvasEl: HTMLCanvasElement | null = $state(null);
    let maskCanvasEl: HTMLCanvasElement | null = null;
    let currentFrameIndex = $state(0);
    let renderedFrameIndex: number | null = $state(null);
    let renderedFrameNumber: number | null = $state(null);
    let currentSourceTime = $state(0);
    let isPlaying = $state(false);
    let isLoading = $state(true);
    let debugSample = $state<PlaybackDebugSample | null>(null);
    let diagnosticsJson = $state('');
    let lastDebugKey: string | null = null;
    let frameImages = $state<(HTMLImageElement | null)[]>([]);
    let loadVersion = 0;
    let playbackStartMs: number | null = null;
    let playbackStartTime = 0;
    let rafId: number | null = null;
    let cachedPayloadKey: string | null = null;
    let cachedPayload: PlaybackAnnotationPayload = { masks: [], boxes: [] };

    const clampFrameIndex = (value: number): number => {
        if (frames.length === 0) {
            return 0;
        }

        return Math.max(0, Math.min(value, frames.length - 1));
    };

    const getFrameAtIndex = (frameIndex: number): FrameView | null => {
        return frames[clampFrameIndex(frameIndex)] ?? null;
    };

    const getPlaybackEndTime = (): number => {
        if (frames.length === 0) {
            return 0;
        }

        const lastFrameWindowTarget = getFrameWindowTarget({
            frames,
            frameIndex: frames.length - 1,
            videoDuration: durationSeconds
        });

        return (
            lastFrameWindowTarget?.windowEndTimestamp ??
            frames[frames.length - 1]?.frame_timestamp_s ??
            0
        );
    };

    const objectFitClass = $derived(objectFit === 'cover' ? 'object-cover' : 'object-contain');
    const currentFrame = $derived(getFrameAtIndex(currentFrameIndex));
    const currentFrameNumber = $derived(currentFrame?.frame_number ?? 0);
    const currentFrameTimestamp = $derived(currentFrame?.frame_timestamp_s ?? 0);
    const totalFrames = $derived(Math.max(frames.length, 1));
    const totalDuration = $derived(
        typeof durationSeconds === 'number' && Number.isFinite(durationSeconds)
            ? durationSeconds
            : getPlaybackEndTime()
    );

    const createFrameUrl = (frame: FrameView, index: number) =>
        resolveFrameImageUrl?.(frame, index) ??
        getGridFrameURL({
            sampleId: frame.sample_id,
            quality: 'high',
            renderedWidth: sampleWidth,
            renderedHeight: sampleHeight
        });

    const loadImage = (url: string): Promise<HTMLImageElement> =>
        new Promise((resolve, reject) => {
            const image = new Image();
            image.decoding = 'async';
            image.onload = () => resolve(image);
            image.onerror = () => reject(new Error(`Failed to load frame image: ${url}`));
            image.src = url;
        });

    const cancelPlaybackLoop = () => {
        if (rafId !== null) {
            cancelAnimationFrame(rafId);
            rafId = null;
        }
    };

    function getCachedPayload(frame: FrameView | null): PlaybackAnnotationPayload {
        if (!frame || $isHidden || !showAnnotations) {
            cachedPayloadKey = null;
            cachedPayload = { masks: [], boxes: [] };
            return cachedPayload;
        }

        const key = [
            frame.sample_id,
            $showBoundingBoxesForSegmentationStore ? '1' : '0',
            $colorVersion
        ].join(':');

        if (cachedPayloadKey === key) {
            return cachedPayload;
        }

        cachedPayload = buildPlaybackAnnotationPayload({
            frame,
            showBoundingBoxesForSegmentation: $showBoundingBoxesForSegmentationStore,
            customLabelColors: $customLabelColorsStore
        });
        cachedPayloadKey = key;
        return cachedPayload;
    }

    function updateDebug({
        source,
        strategy,
        frameIndex,
        sourceTime
    }: {
        source: 'raf' | 'event';
        strategy: 'midpoint' | 'frame_start';
        frameIndex: number;
        sourceTime: number;
    }) {
        if (!showDebug && !testDiagnosticsId) {
            return;
        }

        const frame = getFrameAtIndex(frameIndex);
        const frameStartSelection = selectPlaybackFrame({
            frames,
            sourceTime,
            strategy: 'frame_start'
        });
        const midpointSelection = selectPlaybackFrame({
            frames,
            sourceTime,
            strategy: 'midpoint'
        });
        const windowTarget = getFrameWindowTarget({
            frames,
            frameIndex,
            videoDuration: durationSeconds
        });

        const nextSample: PlaybackDebugSample = {
            clockTime: performance.now(),
            currentTime: sourceTime,
            mediaTime: null,
            sourceTime,
            selectedFrameNumber: frame?.frame_number ?? null,
            selectedFrameTimestamp: frame?.frame_timestamp_s ?? null,
            windowStartTimestamp: windowTarget?.windowStartTimestamp ?? null,
            windowEndTimestamp: windowTarget?.windowEndTimestamp ?? null,
            nextFrameTimestamp: frames[frameIndex + 1]?.frame_timestamp_s ?? null,
            renderedFrameNumber,
            requestedFrameIndex: currentFrameIndex,
            resolvedFrameIndex: frameIndex,
            pinnedFrameIndex: isPlaying ? null : frameIndex,
            inFlightSeekTargetTime: null,
            selectorInvariantHolds: true,
            source,
            strategy,
            selectionModeOverride: undefined,
            frameStartFrameNumber: frameStartSelection.frame?.frame_number ?? null,
            midpointFrameNumber: midpointSelection.frame?.frame_number ?? null
        };

        if (showDebug) {
            debugSample = nextSample;
        }

        if (testDiagnosticsId) {
            diagnosticsJson = JSON.stringify({
                playerId: testDiagnosticsId,
                source,
                strategy,
                currentTime: sourceTime,
                mediaTime: null,
                sourceTime,
                isPlaying,
                selectedFrameIndex: frameIndex,
                selectedFrameNumber: frame?.frame_number ?? null,
                renderedFrameIndex,
                renderedFrameNumber,
                requestedFrameIndex: currentFrameIndex,
                resolvedFrameIndex: frameIndex,
                pinnedFrameIndex: isPlaying ? null : frameIndex
            });
        }

        const debugKey = `${source}:${strategy}:${frame?.frame_number ?? 'none'}:${renderedFrameNumber}`;
        if (showDebug && debugKey !== lastDebugKey) {
            console.debug('video-playback-debug', nextSample);
            lastDebugKey = debugKey;
        }
    }

    function drawFrame({
        frameIndex,
        source,
        strategy,
        sourceTime
    }: {
        frameIndex: number;
        source: 'raf' | 'event';
        strategy: 'midpoint' | 'frame_start';
        sourceTime: number;
    }) {
        if (!canvasEl || !maskCanvasEl) {
            return;
        }

        const image = frameImages[frameIndex];
        const frame = getFrameAtIndex(frameIndex);
        if (!image || !frame) {
            return;
        }

        const canvasCtx = canvasEl.getContext('2d');
        const maskCtx = maskCanvasEl.getContext('2d');
        if (!canvasCtx || !maskCtx) {
            return;
        }

        const payload = getCachedPayload(frame);
        const scaleX = canvasEl.clientWidth / sampleWidth || 1;
        const scaleY = canvasEl.clientHeight / sampleHeight || 1;

        renderCanvasPlaybackFrame({
            canvasCtx,
            maskCtx,
            maskCanvas: maskCanvasEl,
            mediaSource: image,
            sampleWidth,
            sampleHeight,
            payload,
            scaleX,
            scaleY
        });

        currentFrameIndex = frameIndex;
        renderedFrameIndex = frameIndex;
        renderedFrameNumber = frame.frame_number;
        currentSourceTime = sourceTime;
        updateDebug({ source, strategy, frameIndex, sourceTime });
    }

    function renderCurrentFrame(source: 'raf' | 'event' = 'event') {
        drawFrame({
            frameIndex: currentFrameIndex,
            source,
            strategy: isPlaying ? 'midpoint' : 'frame_start',
            sourceTime: isPlaying ? currentSourceTime : (currentFrame?.frame_timestamp_s ?? 0)
        });
    }

    function stopPlayback() {
        isPlaying = false;
        playbackStartMs = null;
        cancelPlaybackLoop();
    }

    function playbackTick(now: number) {
        if (!isPlaying) {
            return;
        }

        if (playbackStartMs == null) {
            playbackStartMs = now;
        }

        const elapsedSeconds = (now - playbackStartMs) / 1000;
        const sourceTime = Math.min(playbackStartTime + elapsedSeconds, getPlaybackEndTime());
        const selection = selectPlaybackFrame({
            frames,
            sourceTime,
            strategy: 'midpoint'
        });
        const nextFrameIndex = selection.index ?? currentFrameIndex;

        if (nextFrameIndex !== renderedFrameIndex || renderedFrameIndex == null) {
            drawFrame({
                frameIndex: nextFrameIndex,
                source: 'raf',
                strategy: 'midpoint',
                sourceTime
            });
        }

        if (sourceTime >= getPlaybackEndTime()) {
            stopPlayback();
            return;
        }

        rafId = requestAnimationFrame(playbackTick);
    }

    function startPlayback() {
        if (isLoading || frames.length === 0) {
            return;
        }

        if (currentFrameIndex >= frames.length - 1) {
            currentFrameIndex = 0;
        }

        const frame = getFrameAtIndex(currentFrameIndex);
        playbackStartTime = frame?.frame_timestamp_s ?? 0;
        currentSourceTime = playbackStartTime;
        playbackStartMs = null;
        isPlaying = true;
        cancelPlaybackLoop();
        rafId = requestAnimationFrame(playbackTick);
    }

    function togglePlayback() {
        if (isPlaying) {
            stopPlayback();
            renderCurrentFrame();
            return;
        }

        startPlayback();
    }

    function selectFrameIndex(nextFrameIndex: number) {
        const safeIndex = clampFrameIndex(nextFrameIndex);
        stopPlayback();
        drawFrame({
            frameIndex: safeIndex,
            source: 'event',
            strategy: 'frame_start',
            sourceTime: getFrameAtIndex(safeIndex)?.frame_timestamp_s ?? 0
        });
    }

    function handleSeekChange(nextValues: number[]) {
        const [nextValue = 0] = nextValues;
        selectFrameIndex(Math.round(nextValue));
    }

    onMount(() => {
        maskCanvasEl = document.createElement('canvas');
        maskCanvasEl.width = sampleWidth;
        maskCanvasEl.height = sampleHeight;

        return () => {
            cancelPlaybackLoop();
        };
    });

    $effect(() => {
        if (!canvasEl || frames.length === 0) {
            return;
        }

        canvasEl.width = sampleWidth;
        canvasEl.height = sampleHeight;
    });

    $effect(() => {
        cancelPlaybackLoop();
        isPlaying = false;
        isLoading = true;
        const nextFrameUrls = frames.map(createFrameUrl);
        frameImages = [];
        const nextLoadVersion = ++loadVersion;
        const safeInitialFrameIndex = clampFrameIndex(initialFrameIndex);

        void Promise.all(nextFrameUrls.map(loadImage))
            .then((images) => {
                if (loadVersion !== nextLoadVersion) {
                    return;
                }

                frameImages = images;
                isLoading = false;
                drawFrame({
                    frameIndex: safeInitialFrameIndex,
                    source: 'event',
                    strategy: 'frame_start',
                    sourceTime: getFrameAtIndex(safeInitialFrameIndex)?.frame_timestamp_s ?? 0
                });
            })
            .catch((error) => {
                if (loadVersion !== nextLoadVersion) {
                    return;
                }
                console.error('Failed to preload frame sequence', error);
                frameImages = [];
                isLoading = false;
            });
    });

    $effect(() => {
        void $isHidden;
        void $showBoundingBoxesForSegmentationStore;
        void $colorVersion;
        void $customLabelColorsStore;
        void showAnnotations;

        cachedPayloadKey = null;
        if (!isLoading && frameImages[currentFrameIndex]) {
            renderCurrentFrame();
        }
    });
</script>

<div
    class={`relative flex min-h-0 flex-1 flex-col overflow-hidden rounded-lg bg-black ${className}`}
    data-playback-player-id={testDiagnosticsId}
>
    <div class="relative flex min-h-0 flex-1 items-center justify-center bg-black">
        {#if showDebug}
            <VideoPlaybackDebugBadge sample={debugSample} />
        {/if}
        {#if isLoading}
            <div class="absolute inset-0 flex items-center justify-center">
                <Spinner />
            </div>
        {/if}
        <canvas
            bind:this={canvasEl}
            class={`block h-full w-full ${objectFitClass}`}
            data-testid="canvas-video-player-canvas"
        ></canvas>
        {#if testDiagnosticsId}
            <div
                class="hidden"
                aria-hidden="true"
                data-testid={`video-playback-diagnostics-${testDiagnosticsId}`}
            >
                {diagnosticsJson}
            </div>
        {/if}
    </div>

    {#if showControls}
        <div
            class="flex items-center gap-3 border-t border-white/10 bg-black px-3 py-2 text-sm text-white"
        >
            <button
                type="button"
                class="rounded border border-white/20 px-3 py-1 font-medium hover:bg-white/10"
                aria-label={isPlaying ? 'Pause video' : 'Play video'}
                onclick={togglePlayback}
                disabled={isLoading || frames.length === 0}
            >
                {isPlaying ? 'Pause' : 'Play'}
            </button>
            <Slider
                type="multiple"
                min={0}
                max={Math.max(frames.length - 1, 0)}
                step={1}
                value={[currentFrameIndex]}
                class="flex-1"
                aria-label="Seek video frame"
                data-testid="canvas-video-player-slider"
                onValueChange={handleSeekChange}
                disabled={isLoading || frames.length === 0}
            />
            <div
                class="min-w-40 text-right font-mono text-xs"
                data-testid="canvas-video-player-readout"
            >
                <div>
                    Frame {currentFrameNumber} <span class="text-white/70">/ {totalFrames}</span>
                </div>
                <div class="text-white/70">
                    {currentFrameTimestamp.toFixed(3)}s / {totalDuration.toFixed(3)}s
                </div>
            </div>
        </div>
    {/if}
</div>
