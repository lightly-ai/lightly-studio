<script lang="ts">
    import { onMount } from 'svelte';
    import { useCuboidFaceResize } from './useCuboidFaceResize.svelte';
    type ResizeParams = Parameters<typeof useCuboidFaceResize>[0];
    interface Props extends ResizeParams {
        onReady: (resize: ReturnType<typeof useCuboidFaceResize>) => void;
    }
    let {
        onReady,
        getAnnotation,
        onResizeStart,
        onResizeCancel,
        onResizePreview,
        onResizeEnd
    }: Props = $props();
    const resize = useCuboidFaceResize({
        getAnnotation: () => getAnnotation(),
        onResizeStart: () => onResizeStart?.(),
        onResizeCancel: () => onResizeCancel?.(),
        onResizePreview: (payload) => onResizePreview(payload),
        onResizeEnd: (payload) => onResizeEnd?.(payload)
    });
    onMount(() => onReady(resize));
</script>
