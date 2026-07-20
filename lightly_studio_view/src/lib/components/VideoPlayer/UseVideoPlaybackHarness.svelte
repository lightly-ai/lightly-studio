<script lang="ts">
    import { useVideoPlayback } from './useVideoPlayback.svelte';

    interface Props {
        videoEl: HTMLVideoElement | null;
        regionEl?: HTMLDivElement | null;
        src: string;
        startTimeS: number | null;
        initialMuted?: boolean;
        onReady: (result: ReturnType<typeof useVideoPlayback>) => void;
    }

    const { videoEl, regionEl = null, src, startTimeS, initialMuted, onReady }: Props = $props();

    const playback = useVideoPlayback({
        getVideoEl: () => videoEl,
        getRegionEl: () => regionEl,
        getSrc: () => src,
        getStartTimeS: () => startTimeS,
        initialMuted
    });

    onReady(playback);
</script>
