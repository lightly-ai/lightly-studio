<script lang="ts">
    import { page } from '$app/state';
    import { useCaption } from '$lib/hooks/useCaption/useCaption';
    import { Check } from '@lucide/svelte';
    import type { CaptionView } from '$lib/api/lightly_studio_local';
    import * as Popover from '$lib/components/ui/popover/index.js';
    import Button from '$lib/components/ui/button/button.svelte';
    import { Trash2 } from '@lucide/svelte';

    const {
        caption: captionProp,
        onDeleteCaption,
        onUpdate
    }: {
        caption: CaptionView;
        onDeleteCaption: (e: MouseEvent) => void;
        onUpdate: () => void;
    } = $props();

    const { isEditingMode } = page.data.globalStorage;

    const captionId = $derived(captionProp.caption_id);

    const { caption: captionResp, updateCaptionText } = $derived(
        useCaption({
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
    let showDeleteConfirmation = $state(false);
</script>

<div
    class="bg-card text-diffuse-foreground mb-2 gap-2 rounded-sm px-4 py-3 text-left align-baseline transition-colors"
    data-caption-id={caption.caption_id}
>
    <div class="flex flex-1 flex-col gap-1">
        <div class="text-sm font-medium" data-testid="caption-text">
            {#if $isEditingMode}
                <div class="flex items-center gap-2">
                    <input
                        class="border-input bg-background ring-offset-background placeholder:text-muted-foreground focus-visible:ring-ring flex h-10 flex-1 rounded-md border px-3 py-2 text-base file:border-0 file:bg-transparent file:text-sm file:font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 md:text-sm"
                        type="text"
                        bind:value={captionText}
                        disabled={isSaving}
                        placeholder="Update caption"
                        use:preventViewerNavigation
                    />
                    <button
                        type="button"
                        class="border-primary bg-primary text-primary-foreground disabled:border-input disabled:bg-background disabled:text-muted-foreground inline-flex h-9 w-9 items-center justify-center rounded-md border transition disabled:cursor-not-allowed disabled:opacity-50"
                        onclick={saveCaption}
                        disabled={!isDirty || isSaving}
                        aria-label="Save caption"
                    >
                        <Check class="size-5" />
                    </button>
                    <Popover.Root bind:open={showDeleteConfirmation}>
                        <Popover.Trigger>
                            <Trash2 class="size-6" />
                        </Popover.Trigger>
                        <Popover.Content>
                            You are going to delete this caption. This action cannot be undone.
                            <div class="mt-2 flex justify-end gap-2">
                                <Button
                                    variant="destructive"
                                    size="sm"
                                    onclick={(e: MouseEvent) => {
                                        e.stopPropagation();
                                        onDeleteCaption(e);
                                        showDeleteConfirmation = false;
                                    }}>Delete</Button
                                >
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onclick={(e: MouseEvent) => {
                                        e.stopPropagation();
                                        showDeleteConfirmation = false;
                                    }}>Cancel</Button
                                >
                            </div>
                        </Popover.Content>
                    </Popover.Root>
                </div>
            {:else}
                <span class="text-sm">{caption.text}</span>
            {/if}
        </div>
    </div>
</div>
