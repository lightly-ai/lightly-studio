<script lang="ts">
    import type { ComponentProps } from 'svelte';
    import ProjectionOverlay from '../ProjectionOverlay.svelte';

    interface Props {
        label: string;
        imageUrl: string | null;
        /** The point cloud and annotations drawn over the image. */
        overlay: ComponentProps<typeof ProjectionOverlay>;
    }

    const { label, imageUrl, overlay }: Props = $props();
</script>

<div class="relative mx-auto w-fit max-w-full">
    <img
        src={imageUrl ?? undefined}
        alt={`${label} enlarged`}
        class="block max-h-[80vh] max-w-full rounded-md object-contain"
    />
    <ProjectionOverlay {...overlay} />
</div>
