<script lang="ts">
    import { useVideo } from './useVideo.svelte';

    interface Props {
        onReady: (result: ReturnType<typeof useVideo>) => void;
    }

    const { onReady }: Props = $props();
    const result = useVideo();

    onReady(result);
</script>
