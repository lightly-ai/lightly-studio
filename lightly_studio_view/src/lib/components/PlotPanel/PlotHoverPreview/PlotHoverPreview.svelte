<script lang="ts">
    import { Spinner } from '$lib/components';
    import type { ThumbnailUrlResolver } from './thumbnailUrlResolver';

    interface Props {
        sampleId: string;
        resolveThumbnailUrl: ThumbnailUrlResolver;
    }

    let { sampleId, resolveThumbnailUrl }: Props = $props();

    let loadedUrl = $state<string | null>(null);
    let failed = $state(false);

    // Show a spinner right away and swap to the image once it is fully loaded;
    // thumbnails can take a while on first request (backend resize).
    $effect(() => {
        const currentSampleId = sampleId;
        let cancelled = false;
        loadedUrl = null;
        failed = false;
        void resolveThumbnailUrl(currentSampleId).then((url) => {
            if (cancelled) return;
            if (url === null) {
                failed = true;
                return;
            }
            const image = new Image();
            image.onload = () => {
                if (!cancelled) loadedUrl = url;
            };
            image.onerror = () => {
                if (!cancelled) failed = true;
            };
            image.src = url;
        });
        return () => {
            cancelled = true;
        };
    });
</script>

{#if !failed}
    <div
        class="flex h-32 w-32 items-center justify-center overflow-hidden rounded-md border border-border bg-black shadow-lg"
        data-testid="plot-hover-preview"
    >
        {#if loadedUrl}
            <img
                src={loadedUrl}
                alt="Hovered sample preview"
                class="block h-full w-full object-contain"
            />
        {:else}
            <Spinner size="small" />
        {/if}
    </div>
{/if}
