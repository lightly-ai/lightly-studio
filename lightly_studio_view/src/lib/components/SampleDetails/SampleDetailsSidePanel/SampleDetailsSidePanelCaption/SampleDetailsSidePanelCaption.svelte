<script lang="ts">
    import { page } from '$app/state';
    import { Button } from '$lib/components/ui';
    import { useCaption } from '$lib/hooks/useCaption/useCaption';
    import type { CaptionView } from '$lib/api/lightly_studio_local';

    const {
        caption: captionProp,
        onUpdate
    }: {
        caption: CaptionView;
        onUpdate: () => void;
    } = $props();

    const { isEditingMode } = page.data.globalStorage;
    const { datasetId } = page.data;

    const captionId = $derived(captionProp.caption_id);

    const { caption: captionResp, updateCaptionText } = $derived(
        useCaption({
            datasetId,
            captionId,
            onUpdate
        })
    );

    const caption = $derived($captionResp.data || captionProp);

    let captionText = $state('');
    let isSaving = $state(false);

    $effect(() => {
        captionText = caption.text ?? '';
    });

    const isDirty = $derived(captionText !== (caption.text ?? ''));

    const saveCaption = async () => {
        if (!isDirty || isSaving) {
            return;
        }
        isSaving = true;
        try {
            await updateCaptionText(captionText);
        } finally {
            isSaving = false;
        }
    };

    const handleKeyDown = (event: KeyboardEvent) => {
        const isNavigationKey =
            ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(event.key) ||
            event.code === 'Space';
        if (isNavigationKey) {
            event.stopPropagation();
            event.stopImmediatePropagation?.();
        }

        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            saveCaption();
        }
    };

    const preventViewerNavigation = (node: HTMLElement) => {
        const listener = (event: Event) => handleKeyDown(event as KeyboardEvent);
        node.addEventListener('keydown', listener, true);
        return {
            destroy: () => node.removeEventListener('keydown', listener, true)
        };
    };
</script>

<div
    class="mb-2 gap-2 rounded-sm bg-card px-4 py-3 text-left align-baseline text-diffuse-foreground transition-colors"
    data-caption-id={caption.caption_id}
>
    <div class="flex flex-1 flex-col gap-1">
        <div class="text-sm font-medium" data-testid="sample-details-panel-caption-text">
            {#if $isEditingMode}
                <div class="flex flex-col gap-2">
                    <input
                        class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-base ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 md:text-sm"
                        type="text"
                        bind:value={captionText}
                        disabled={isSaving}
                        placeholder="Update caption"
                        use:preventViewerNavigation
                    />
                    <div class="flex justify-end">
                        <Button
                            type="button"
                            size="sm"
                            disabled={!isDirty || isSaving}
                            onclick={saveCaption}
                        >
                            {isSaving ? 'Saving...' : 'Save'}
                        </Button>
                    </div>
                </div>
            {:else}
                <span class="text-sm">{caption.text}</span>
            {/if}
        </div>
    </div>
</div>
