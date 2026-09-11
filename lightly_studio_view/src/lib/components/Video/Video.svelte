<script lang="ts">
    import { PUBLIC_VIDEOS_FRAMES_MEDIA_URL } from '$env/static/public';
    import type { FrameView, VideoFrameView, VideoView } from '$lib/api/lightly_studio_local';
    import { useRecoverableVideo } from '$lib/hooks';
    import { getGridFrameURL, getGridThumbnailRequestSize, getVideoURLById } from '$lib/utils';
    import { findFrame } from '$lib/utils/frame';

    interface VideoProps {
        video: VideoView;
        frames: FrameView[];
        update: (frame: FrameView | VideoFrameView | null, index: number | null) => void;
        videoEl: HTMLVideoElement | null;
        controls?: boolean;
        muted?: boolean;
        playsinline?: boolean;
        preload?: 'auto' | 'metadata' | 'none';
        className?: string;
        posterSize?: number;
        handleMouseEnter?: (event: MouseEvent) => void;
        handleMouseLeave?: (event: MouseEvent) => void;
        onplay?: () => void;
        onseeked?: (event: Event) => void;
        mediaSourceUrl?: string;
        recoveryWatchdogMs?: number;
    }

    let {
        video,
        update,
        videoEl = $bindable(),
        frames = [],
        muted = true,
        playsinline = true,
        controls = false,
        preload = 'metadata',
        className = '',
        posterSize,
        handleMouseEnter = () => {},
        handleMouseLeave = () => {},
        onplay = () => {},
        onseeked = () => {},
        mediaSourceUrl = $bindable(''),
        recoveryWatchdogMs
    }: VideoProps = $props();

    let previousIndex: number | null = null;
    let frameRequestId: number | null = null;
    let previousVideoSampleId: string | null = null;
    const recovery = useRecoverableVideo({
        getVideoEl: () => videoEl,
        getSourceUrl: () => getVideoURLById(video.sample_id),
        getWatchdogMs: () => recoveryWatchdogMs
    });

    $effect(() => {
        mediaSourceUrl = recovery.sourceUrl;
    });
    const posterUrl = $derived.by(() => {
        if (frames.length === 0) {
            return null;
        }

        if (!posterSize) {
            return `${PUBLIC_VIDEOS_FRAMES_MEDIA_URL}/${frames[0].sample_id}`;
        }

        const requestedSize = getGridThumbnailRequestSize(
            posterSize,
            globalThis.window?.devicePixelRatio || 1
        );
        // Always use high quality (JPEG) for grid posters to maintain performance.
        return getGridFrameURL({
            sampleId: frames[0].sample_id,
            quality: 'high',
            renderedWidth: requestedSize,
            renderedHeight: requestedSize
        });
    });

    function startFrameLoop() {
        clearFrameLoop();

        function tick() {
            if (!videoEl) {
                frameRequestId = null;
                return;
            }
            const { frame, index } = findFrame({ frames, currentTime: videoEl.currentTime });

            if (index !== null && previousIndex !== index) {
                update(frame, index);
                previousIndex = index;
            }

            frameRequestId = requestAnimationFrame(tick);
        }

        frameRequestId = requestAnimationFrame(tick);
    }

    function clearFrameLoop() {
        if (frameRequestId !== null) {
            cancelAnimationFrame(frameRequestId);
            frameRequestId = null;
        }
    }

    $effect(() => {
        if (!videoEl) return;

        const currentVideoSampleId = video.sample_id;

        if (previousVideoSampleId !== null && previousVideoSampleId !== currentVideoSampleId) {
            previousIndex = null;
            videoEl.pause();
            videoEl.removeAttribute('src');
            videoEl.load();
        }

        previousVideoSampleId = currentVideoSampleId;
        startFrameLoop();

        return () => {
            clearFrameLoop();
        };
    });
</script>

<div class="relative h-full w-full">
    <video
        bind:this={videoEl}
        {muted}
        {playsinline}
        {preload}
        {controls}
        src={recovery.sourceUrl}
        class={className}
        onmouseenter={handleMouseEnter}
        onmouseleave={handleMouseLeave}
        {onplay}
        {onseeked}
        poster={posterUrl}
    ></video>
    {#if recovery.terminalError}
        <div
            role="status"
            aria-live="polite"
            class="absolute inset-0 z-[10] flex items-center justify-center bg-black/70 p-2 text-center text-xs font-medium text-white"
        >
            {recovery.terminalError}
        </div>
    {/if}
</div>
