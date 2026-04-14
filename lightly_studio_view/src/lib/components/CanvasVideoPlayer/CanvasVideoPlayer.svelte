<script lang="ts">
    import { onMount } from 'svelte';
    import type { FrameView } from '$lib/api/lightly_studio_local';
    import type { SampleImageObjectFit } from '$lib/components/SampleImage/types';
    import { Slider } from '$lib/components/ui/slider';
    import { useCustomLabelColors } from '$lib/hooks/useCustomLabelColors';
    import { useHideAnnotations } from '$lib/hooks/useHideAnnotations';
    import { useSettings } from '$lib/hooks/useSettings';
    import {
        getFrameWindowTarget,
        selectPlaybackFrame,
        type PlaybackSelectionStrategy
    } from '$lib/utils/frame';
    import type { PlaybackDebugSample } from '$lib/components/VideoPlaybackDebugBadge/VideoPlaybackDebugBadge.svelte';
    import VideoPlaybackDebugBadge from '$lib/components/VideoPlaybackDebugBadge/VideoPlaybackDebugBadge.svelte';
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

    export type SelectionModeOverride = 'auto' | 'start' | 'mid' | 'hybrid';

    type CanvasVideoPlayerProps = {
        src: string;
        frames: FrameView[];
        sampleWidth: number;
        sampleHeight: number;
        initialFrameIndex?: number;
        className?: string;
        objectFit?: SampleImageObjectFit;
        showControls?: boolean;
        showDebug?: boolean;
        showSelectionModeDebugControls?: boolean;
        selectionModeOverride?: SelectionModeOverride;
        showAnnotations?: boolean;
        autoplay?: boolean;
        loop?: boolean;
        testDiagnosticsId?: string;
        onFrameChange?: (sample: PlaybackSample<FrameView>) => void;
        onPlayStateChange?: (isPlaying: boolean) => void;
        onSeek?: (frameIndex: number) => void;
    };

    let {
        src,
        frames,
        sampleWidth,
        sampleHeight,
        initialFrameIndex = 0,
        className = '',
        objectFit = 'contain',
        showControls = true,
        showDebug = false,
        showSelectionModeDebugControls = false,
        selectionModeOverride = 'auto',
        showAnnotations = true,
        autoplay = false,
        loop = false,
        testDiagnosticsId,
        onFrameChange = () => {},
        onPlayStateChange = () => {},
        onSeek = () => {}
    }: CanvasVideoPlayerProps = $props();

    const { customLabelColorsStore, colorVersion } = useCustomLabelColors();
    const { isHidden } = useHideAnnotations();
    const { showBoundingBoxesForSegmentationStore } = useSettings();

    let videoEl: HTMLVideoElement | null = $state(null);
    let canvasEl: HTMLCanvasElement | null = $state(null);
    let maskCanvasEl: HTMLCanvasElement | null = null;

    let requestedFrameIndex = $state(0);
    let resolvedFrameIndex = $state(0);
    let pinnedFrameIndex = $state<number | null>(null);
    let isPlaying = $state(false);
    let pendingHybridSeekPlaybackSamples = $state(0);
    let debugSample = $state<PlaybackDebugSample | null>(null);
    let diagnosticsJson = $state('');
    let lastDebugKey: string | null = null;
    let renderedFrameNumber: number | null = $state(null);
    let renderedFrameIndex: number | null = $state(null);
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

    const clampFrameIndex = (value: number): number => {
        if (frames.length === 0) {
            return 0;
        }

        return Math.max(0, Math.min(value, frames.length - 1));
    };

    const getFrameAtIndex = (frameIndex: number): FrameView | null => {
        return frames[clampFrameIndex(frameIndex)] ?? null;
    };

    const objectFitClass = $derived(objectFit === 'cover' ? 'object-cover' : 'object-contain');
    const displayedFrameIndex = $derived(pinnedFrameIndex ?? resolvedFrameIndex);
    const currentFrame = $derived(getFrameAtIndex(displayedFrameIndex));
    const currentFrameNumber = $derived(currentFrame?.frame_number ?? 0);
    const currentFrameTimestamp = $derived(currentFrame?.frame_timestamp_s ?? 0);
    const totalFrames = $derived(Math.max(frames.length, 1));
    const totalDuration = $derived.by(() => {
        const duration = videoEl?.duration;
        if (typeof duration === 'number' && Number.isFinite(duration)) {
            return duration;
        }

        return frames.length > 0 ? (frames[frames.length - 1]?.frame_timestamp_s ?? 0) : 0;
    });
    const selectionModeButtons: Array<Exclude<SelectionModeOverride, 'auto'>> = [
        'start',
        'mid',
        'hybrid'
    ];

    function resolveAutomaticSelectionStrategy(source: PlaybackSource): PlaybackSelectionStrategy {
        if (source === 'event' || !isPlaying || pendingHybridSeekPlaybackSamples > 0) {
            return 'frame_start';
        }

        return 'midpoint';
    }

    function resolveSelectionStrategy(source: PlaybackSource): PlaybackSelectionStrategy {
        if (selectionModeOverride === 'start') {
            return 'frame_start';
        }

        if (selectionModeOverride === 'mid') {
            return 'midpoint';
        }

        return resolveAutomaticSelectionStrategy(source);
    }

    function updateDebugSample(sample: PlaybackSample<FrameView>) {
        if (!showDebug && !testDiagnosticsId) {
            return;
        }

        const frameStartSelection = selectPlaybackFrame({
            frames,
            sourceTime: sample.selection.sourceTime,
            strategy: 'frame_start'
        });
        const midpointSelection = selectPlaybackFrame({
            frames,
            sourceTime: sample.selection.sourceTime,
            strategy: 'midpoint'
        });
        const nextSample: PlaybackDebugSample = {
            clockTime: sample.clockTime,
            currentTime: sample.currentTime,
            mediaTime: sample.mediaTime,
            sourceTime: sample.selection.sourceTime,
            selectedFrameNumber: sample.selection.frame?.frame_number ?? null,
            selectedFrameTimestamp: sample.selection.selectedTimestamp,
            windowStartTimestamp: sample.selection.windowStartTimestamp,
            windowEndTimestamp: sample.selection.windowEndTimestamp,
            nextFrameTimestamp: sample.selection.nextTimestamp,
            renderedFrameNumber,
            requestedFrameIndex,
            resolvedFrameIndex,
            pinnedFrameIndex,
            inFlightSeekTargetTime: pendingSeekTargetTime,
            selectorInvariantHolds: sample.selection.selectorInvariantHolds,
            source: sample.source,
            strategy: sample.selection.strategy,
            selectionModeOverride,
            frameStartFrameNumber: frameStartSelection.frame?.frame_number ?? null,
            midpointFrameNumber: midpointSelection.frame?.frame_number ?? null
        };

        if (showDebug) {
            debugSample = nextSample;
        }

        if (testDiagnosticsId) {
            diagnosticsJson = JSON.stringify({
                playerId: testDiagnosticsId,
                source: sample.source,
                strategy: sample.selection.strategy,
                currentTime: sample.currentTime,
                mediaTime: sample.mediaTime,
                sourceTime: sample.selection.sourceTime,
                isPlaying,
                selectedFrameIndex: sample.selection.index,
                selectedFrameNumber: sample.selection.frame?.frame_number ?? null,
                renderedFrameIndex,
                renderedFrameNumber,
                requestedFrameIndex,
                resolvedFrameIndex,
                pinnedFrameIndex
            });
        }

        const debugKey = `${nextSample.source}:${nextSample.strategy}:${nextSample.selectedFrameNumber}:${nextSample.renderedFrameNumber}:${nextSample.selectorInvariantHolds}`;
        if (showDebug && (debugKey !== lastDebugKey || !nextSample.selectorInvariantHolds)) {
            console.debug('video-playback-debug', nextSample);
            lastDebugKey = debugKey;
        }
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
            videoEl,
            sampleWidth,
            sampleHeight,
            payload,
            scaleX,
            scaleY
        });

        renderedFrameIndex = sample.selection.index ?? null;
        renderedFrameNumber = sample.selection.frame?.frame_number ?? null;
        updateDebugSample(sample);
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

    function handlePlaybackSample(sample: PlaybackSample<FrameView>) {
        if (isPlaying && sample.selection.index != null) {
            lastActiveFrameIndex = sample.selection.index;
        }

        if (pendingPauseNormalization && sample.source === 'event') {
            return;
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

        const selectedFrameId = sampleToRender.selection.frame?.sample_id ?? null;
        if (selectedFrameId !== null && selectedFrameId !== lastFrameChangeId) {
            lastFrameChangeId = selectedFrameId;
            onFrameChange(sampleToRender);
        }
    }

    function handleLoadedMetadata() {
        if (!videoEl) {
            return;
        }

        if (!initialFrameApplied) {
            const initialFrame = getFrameAtIndex(initialFrameIndex);
            const initialTime = initialFrame?.frame_timestamp_s ?? 0;

            videoEl.currentTime = initialTime;
            requestedFrameIndex = clampFrameIndex(initialFrameIndex);
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

        requestedFrameIndex = nextFrameIndex;
        inFlightSeekFrameIndex = nextFrameIndex;
        pendingHybridSeekPlaybackSamples = 1;
        pendingSeekTargetTime = pausedSeekTarget?.seekTargetTime ?? nextFrame.frame_timestamp_s;
        onSeek(nextFrameIndex);

        videoEl.currentTime = pendingSeekTargetTime;
    }

    function requestSeek(nextFrameIndex: number) {
        const clampedFrameIndex = clampFrameIndex(nextFrameIndex);
        requestedFrameIndex = clampedFrameIndex;

        if (!isPlaying) {
            pinnedFrameIndex = clampedFrameIndex;
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

    onMount(() => {
        maskCanvasEl = document.createElement('canvas');
        maskCanvasEl.width = sampleWidth;
        maskCanvasEl.height = sampleHeight;
    });

    $effect(() => {
        if (!videoEl || !canvasEl || frames.length === 0) {
            return;
        }

        canvasEl.width = sampleWidth;
        canvasEl.height = sampleHeight;

        const controller = createVideoPlaybackController({
            videoEl,
            frames,
            emitDuplicateFrames: true,
            selectionStrategy: ({ source }) => resolveSelectionStrategy(source),
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
            onPlayStateChange(true);
        };
        const handlePause = () => {
            isPlaying = false;
            pendingHybridSeekPlaybackSamples = 0;

            if (pendingPauseNormalization) {
                const pauseFrameIndex = lastActiveFrameIndex ?? resolvedFrameIndex;
                pendingPauseNormalization = false;
                requestSeek(pauseFrameIndex);
            }

            pendingPauseNormalization = false;
            onPlayStateChange(false);
        };
        const handleEnded = () => {
            isPlaying = false;
            pendingHybridSeekPlaybackSamples = 0;
            pendingPauseNormalization = false;
            onPlayStateChange(false);
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
        void $colorVersion;
        void $customLabelColorsStore;
        void showAnnotations;

        cachedPayloadKey = null;
        if (lastPlaybackSample) {
            drawSample(lastPlaybackSample);
        }
    });
</script>

<div
    class={`relative flex min-h-0 flex-1 flex-col overflow-hidden rounded-lg bg-black ${className}`}
    data-playback-player-id={testDiagnosticsId}
>
    <video
        bind:this={videoEl}
        class="pointer-events-none absolute left-0 top-0 h-px w-px opacity-0"
        {src}
        muted
        playsinline
        preload="auto"
        {loop}
        aria-hidden="true"
        tabindex="-1"
        onloadedmetadata={handleLoadedMetadata}
    ></video>

    <div class="relative flex min-h-0 flex-1 items-center justify-center bg-black">
        {#if showDebug}
            <VideoPlaybackDebugBadge sample={debugSample} />
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
            >
                {isPlaying ? 'Pause' : 'Play'}
            </button>
            <Slider
                type="multiple"
                min={0}
                max={Math.max(frames.length - 1, 0)}
                step={1}
                value={[displayedFrameIndex]}
                class="flex-1"
                aria-label="Seek video frame"
                data-testid="canvas-video-player-slider"
                onValueChange={handleSeekChange}
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
            {#if showSelectionModeDebugControls}
                <div class="flex items-center gap-2" data-testid="selection-mode-debug-controls">
                    {#each selectionModeButtons as mode}
                        <button
                            type="button"
                            class={`rounded border px-2 py-1 font-medium capitalize ${
                                selectionModeOverride === mode
                                    ? 'border-primary bg-white/10 text-white'
                                    : 'border-white/20 text-white/80 hover:bg-white/10'
                            }`}
                            aria-pressed={selectionModeOverride === mode}
                            onclick={() => {
                                selectionModeOverride = mode;
                            }}
                        >
                            {mode}
                        </button>
                    {/each}
                </div>
            {/if}
        </div>
    {/if}
</div>
