<script lang="ts">
    import { onMount } from 'svelte';
    import { useCuboidDraft } from './useCuboidDraft.svelte';
    type DraftParams = Parameters<typeof useCuboidDraft>[0];
    interface Props extends DraftParams {
        onReady: (draft: ReturnType<typeof useCuboidDraft>) => void;
    }
    let { onReady, getCameraMode, getBatch, getTick, getRectangleOnly, onCreate }: Props = $props();
    const draft = useCuboidDraft({
        getRectangleOnly: () => getRectangleOnly?.() ?? false,
        getCameraMode: () => getCameraMode(),
        getBatch: () => getBatch(),
        getTick: () => getTick(),
        onCreate: (placement) => onCreate(placement)
    });
    onMount(() => onReady(draft));
</script>
