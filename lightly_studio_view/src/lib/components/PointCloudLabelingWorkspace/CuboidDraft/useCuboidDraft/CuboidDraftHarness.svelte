<script lang="ts">
    import { onMount } from 'svelte';
    import { useCuboidDraft } from './useCuboidDraft.svelte';
    type DraftParams = Parameters<typeof useCuboidDraft>[0];
    interface Props extends DraftParams {
        onReady: (draft: ReturnType<typeof useCuboidDraft>) => void;
    }
    let { onReady, getCameraMode, getBatch, onCreate }: Props = $props();
    const draft = useCuboidDraft({
        getCameraMode: () => getCameraMode(),
        getBatch: () => getBatch(),
        onCreate: (placement) => onCreate(placement)
    });
    onMount(() => onReady(draft));
</script>
