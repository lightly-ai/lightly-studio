<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import VideoControls from './VideoControls.svelte';

    const { Story } = defineMeta({
        title: 'Components/VideoControls',
        component: VideoControls,
        tags: ['autodocs']
    });

    // The bar owns no state; the Playground wires local state so the scrubber
    // and transport buttons actually respond.
    let currentTimeS = $state(15);
    let durationS = $state(120);
    let isPlaying = $state(false);
    let isMuted = $state(true);
    let isFullscreen = $state(false);

    // Separate state for the short-clip story so its arrow-key stepping is
    // independent of the Playground.
    let shortCurrentTimeS = $state(0);
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

<!--
    Focus the scrubber and press the arrow keys: the step is capped to a
    fraction of the duration so a short clip steps in ~1s increments instead of
    leaping straight to the end.
-->
<Story name="Short clip" asChild>
    <div class="w-[640px] max-w-full bg-black">
        <VideoControls
            currentTimeS={shortCurrentTimeS}
            durationS={4}
            isPlaying={false}
            isMuted={true}
            isFullscreen={false}
            onPlayPause={() => {}}
            onSeek={(timeS) => (shortCurrentTimeS = timeS)}
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
