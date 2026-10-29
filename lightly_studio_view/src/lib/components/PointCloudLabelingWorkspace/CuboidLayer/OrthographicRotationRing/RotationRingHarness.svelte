<script lang="ts">
    import { onMount } from 'svelte';
    import { useRotationRing } from './useRotationRing.svelte';
    type RingCallbacks = Parameters<typeof useRotationRing>[0];
    interface Props extends RingCallbacks {
        onReady: (ring: ReturnType<typeof useRotationRing>) => void;
    }
    let { onReady, onTransformEnd, onInteractionStart, onInteractionCancel }: Props = $props();
    const ring = useRotationRing({
        onTransformEnd: (object, snapshot) => onTransformEnd?.(object, snapshot),
        onInteractionStart: () => onInteractionStart?.(),
        onInteractionCancel: () => onInteractionCancel?.()
    });
    onMount(() => onReady(ring));
</script>
