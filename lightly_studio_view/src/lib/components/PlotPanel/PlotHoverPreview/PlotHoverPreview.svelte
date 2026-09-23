<script lang="ts">
    import { AnnotationItem, Spinner } from '$lib/components';
    import type { Thumbnail, ThumbnailResolver } from './thumbnailUrlResolver';

    const PREVIEW_SIZE = 128;

    interface Props {
        sampleId: string;
        resolveThumbnail: ThumbnailResolver;
    }

    let { sampleId, resolveThumbnail }: Props = $props();

    let loadedThumbnail = $state<Thumbnail | null>(null);
    let sourceWidth = $state(0);
    let sourceHeight = $state(0);
    let failed = $state(false);

    // Show a spinner right away and swap to the image once it is fully loaded;
    // thumbnails can take a while on first request (backend resize).
    $effect(() => {
        const currentSampleId = sampleId;
        let cancelled = false;
        loadedThumbnail = null;
        sourceWidth = 0;
        sourceHeight = 0;
        failed = false;
        void resolveThumbnail(currentSampleId).then((thumbnail) => {
            if (cancelled) return;
            if (thumbnail === null) {
                failed = true;
                return;
            }
            const image = new Image();
            image.onload = () => {
                if (cancelled) return;
                sourceWidth = image.naturalWidth;
                sourceHeight = image.naturalHeight;
                loadedThumbnail = thumbnail;
            };
            image.onerror = () => {
                if (!cancelled) failed = true;
            };
            image.src = thumbnail.url;
        });
        return () => {
            cancelled = true;
        };
    });
</script>

{#if !failed}
    <div
        class="relative flex h-32 w-32 items-center justify-center overflow-hidden rounded-md border border-border bg-black shadow-lg"
        data-testid="plot-hover-preview"
    >
        {#if loadedThumbnail}
            {#if loadedThumbnail.annotation}
                <AnnotationItem
                    annotation={loadedThumbnail.annotation}
                    containerWidth={PREVIEW_SIZE}
                    containerHeight={PREVIEW_SIZE}
                    sample={{
                        width: sourceWidth,
                        height: sourceHeight,
                        url: loadedThumbnail.url
                    }}
                    showLabel={false}
                />
            {:else}
                <img
                    src={loadedThumbnail.url}
                    alt="Hovered sample preview"
                    class="block h-full w-full object-contain"
                />
            {/if}
        {:else}
            <Spinner size="small" />
        {/if}
    </div>
{/if}
