<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import VideoControls from './VideoControls.svelte';

    const { Story } = defineMeta({
        title: 'Components/VideoControls',
        component: VideoControls,
        tags: ['autodocs']
    });
</script>

<script>
    // The bar owns no state; the Playground wires local state so the scrubber
    // and transport buttons actually respond.
    let currentTimeS = $state(15);
    let durationS = $state(120);
    let isPlaying = $state(false);
    let isMuted = $state(true);
    let isFullscreen = $state(false);
</script>

<!-- Rendered on a dark backdrop since the bar is designed to overlay a video. -->
<Story name="Playground" asChild>
    <div class="w-[640px] max-w-full bg-black">
        <VideoControls
            {currentTimeS}
            {durationS}
            {isPlaying}
            {isMuted}
            {isFullscreen}
            onPlayPause={() => (isPlaying = !isPlaying)}
            onSeek={(timeS) => (currentTimeS = timeS)}
            onToggleMute={() => (isMuted = !isMuted)}
            onToggleFullscreen={() => (isFullscreen = !isFullscreen)}
        />
    </div>
</Story>

<Story name="Paused" asChild>
    <div class="w-[640px] max-w-full bg-black">
        <VideoControls
            currentTimeS={15}
            durationS={120}
            isPlaying={false}
            isMuted={true}
            isFullscreen={false}
            onPlayPause={() => {}}
            onSeek={() => {}}
            onToggleMute={() => {}}
            onToggleFullscreen={() => {}}
        />
    </div>
</Story>

<Story name="Playing near end" asChild>
    <div class="w-[640px] max-w-full bg-black">
        <VideoControls
            currentTimeS={118}
            durationS={120}
            isPlaying={true}
            isMuted={false}
            isFullscreen={true}
            onPlayPause={() => {}}
            onSeek={() => {}}
            onToggleMute={() => {}}
            onToggleFullscreen={() => {}}
        />
    </div>
</Story>
