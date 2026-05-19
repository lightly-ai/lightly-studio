<script lang="ts">
    import { useGroupsInfinite } from './';

    interface Props {
        collectionId: string;
        onReady: (result: ReturnType<typeof useGroupsInfinite>) => void;
    }

    const { collectionId, onReady }: Props = $props();
    const result = useGroupsInfinite(() => collectionId);

    onReady(result);
</script>
