<script lang="ts">
    import { onMount } from 'svelte';
    import { useMoveHandle } from './useMoveHandle.svelte';
    type MoveCallbacks = Parameters<typeof useMoveHandle>[0];
    interface Props extends MoveCallbacks {
        onReady: (handle: ReturnType<typeof useMoveHandle>) => void;
    }
    let {
        onReady,
        onTransformEnd,
        onTransformPreview,
        onInteractionStart,
        onInteractionCancel
    }: Props = $props();
    const handle = useMoveHandle({
        onTransformEnd: (object, snapshot) => onTransformEnd?.(object, snapshot),
        onTransformPreview: (object) => onTransformPreview?.(object),
        onInteractionStart: () => onInteractionStart?.(),
        onInteractionCancel: () => onInteractionCancel?.()
    });
    onMount(() => onReady(handle));
</script>
