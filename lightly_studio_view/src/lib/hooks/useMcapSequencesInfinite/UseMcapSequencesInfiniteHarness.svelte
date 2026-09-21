<script lang="ts">
    import { useMcapSequencesInfinite } from './useMcapSequencesInfinite.svelte';

    interface Props {
        collectionId: string;
        onReady: (result: ReturnType<typeof useMcapSequencesInfinite>) => void;
    }

    let { collectionId, onReady }: Props = $props();

    const result = useMcapSequencesInfinite(() => collectionId);

    $effect(() => {
        onReady(result);
    });
</script>
