<script lang="ts">
    import CanvasVideoPlayer from '$lib/components/CanvasVideoPlayer/CanvasVideoPlayer.svelte';
    import {
        buildVideoSyncFixtureFrames,
        VIDEO_SYNC_FIXTURE_HEIGHT,
        VIDEO_SYNC_FIXTURE_VIDEO_SRC,
        VIDEO_SYNC_FIXTURE_WIDTH
    } from '$lib/testing/videoSyncFixture';

    const frames = buildVideoSyncFixtureFrames();
    let showPreview = $state(false);
</script>

<svelte:head>
    <title>Video Sync Fixture</title>
</svelte:head>

<div
    class="flex min-h-screen flex-col gap-8 bg-slate-950 p-8 text-white"
    data-testid="video-sync-fixture-page"
>
    <section class="flex flex-col gap-3">
        <h1 class="text-xl font-semibold">Detail Playback Fixture</h1>
        <div class="h-[360px] max-w-[720px]">
            <CanvasVideoPlayer
                src={VIDEO_SYNC_FIXTURE_VIDEO_SRC}
                {frames}
                sampleWidth={VIDEO_SYNC_FIXTURE_WIDTH}
                sampleHeight={VIDEO_SYNC_FIXTURE_HEIGHT}
                selectionModeOverride="mid"
                testDiagnosticsId="detail-player"
                className="h-full w-full"
            />
        </div>
    </section>

    <section class="flex flex-col gap-3">
        <h2 class="text-xl font-semibold">Grid Hover Preview Fixture</h2>
        <div
            class="flex h-[220px] w-[260px] items-center justify-center rounded-lg border border-white/10 bg-black"
            data-testid="video-sync-preview-trigger"
            role="button"
            aria-label="Hover preview player"
            tabindex="0"
            onmouseenter={() => {
                showPreview = true;
            }}
            onmouseleave={() => {
                showPreview = false;
            }}
        >
            {#if showPreview}
                <CanvasVideoPlayer
                    src={VIDEO_SYNC_FIXTURE_VIDEO_SRC}
                    {frames}
                    sampleWidth={VIDEO_SYNC_FIXTURE_WIDTH}
                    sampleHeight={VIDEO_SYNC_FIXTURE_HEIGHT}
                    selectionModeOverride="mid"
                    testDiagnosticsId="preview-player"
                    showControls={false}
                    autoplay={true}
                    loop={true}
                    className="h-full w-full"
                />
            {:else}
                <div
                    class="flex h-full w-full items-center justify-center rounded-lg bg-slate-900 text-sm text-white/70"
                    data-testid="video-sync-preview-poster"
                >
                    Hover to start preview
                </div>
            {/if}
        </div>
    </section>
</div>
