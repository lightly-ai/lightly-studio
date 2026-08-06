<script lang="ts">
    import { page } from '$app/state';
    import { useCaption } from '$lib/hooks/useCaption/useCaption';
    import { Check, Trash2 } from '@lucide/svelte';
    import type { CaptionView } from '$lib/api/lightly_studio_local';
    import { cn } from '$lib/utils/shadcn.js';
    import { formatTimestampS } from '$lib/components/CaptionSegmentRibbon/captionSegmentRibbon.helpers';
    import {
        getCaptionRepeatGroupId,
        getRepeatGroupColors
    } from '$lib/utils';
    import CaptionMatchScore from './CaptionMatchScore.svelte';
    import CaptionRepetitionBadge from './CaptionRepetitionBadge.svelte';

    interface CaptionFieldProps {
        caption: CaptionView;
        onDeleteCaption: () => void;
        onUpdate: () => void;
        isActive?: boolean;
        onSelect?: () => void;
        /** When true, tint the row by `repeated_caption_group_id`. */
        colorByRepeatGroup?: boolean;
    }

    const {
        caption: captionProp,
        onDeleteCaption,
        onUpdate,
        isActive = false,
        onSelect,
        colorByRepeatGroup = false
    }: CaptionFieldProps = $props();

    const { isEditingMode } = page.data.globalStorage;

    const sampleId = $derived(captionProp.sample_id);

    const { updateCaptionText } = $derived(
        useCaption({
            sampleId,
            onUpdate
        })
    );

    const caption = $derived(captionProp);

    let captionText = $state('');
    let isSaving = $state(false);

    $effect(() => {
        if (isSaving) return;
        // Don't overwrite only when user has typed something different (non-empty local value).
        // When captionText is empty we always sync so existing caption text shows on load.
        if (captionText !== '' && captionText !== (caption.text ?? '')) return;
        captionText = caption.text ?? '';
    });

    const isDirty = $derived(captionText !== (caption.text ?? ''));
    const span = $derived(caption.temporal_span_details);
    const repeatGroupId = $derived(getCaptionRepeatGroupId(caption.metadata_dict));
    const repeatGroupColor = $derived(
        colorByRepeatGroup && repeatGroupId !== null
            ? getRepeatGroupColors(repeatGroupId).color
            : null
    );

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

<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<div
    class={cn(
        'mb-2 gap-2 rounded-sm bg-card px-4 py-3 text-left align-baseline text-diffuse-foreground transition-colors',
        onSelect && 'cursor-pointer hover:bg-accent/40',
        isActive && 'ring-2 ring-primary',
        repeatGroupColor && 'border-l-4'
    )}
    style={repeatGroupColor ? `border-left-color: ${repeatGroupColor}` : undefined}
    data-caption-id={caption.sample_id}
    data-testid="caption-field-row"
    data-active={isActive ? 'true' : undefined}
    data-repeat-colored={repeatGroupColor ? 'true' : undefined}
    onclick={onSelect}
>
    <div class="flex flex-1 flex-col gap-1">
        {#if span}
            <span class="text-xs text-muted-foreground" data-testid="caption-field-time-range">
                {formatTimestampS(span.start_time_s)} – {formatTimestampS(span.end_time_s)}
            </span>
        {/if}
        <div class="text-sm font-medium" data-testid="caption-field">
            {#if $isEditingMode}
                <div class="flex items-center gap-2">
                    <input
                        class="flex h-10 flex-1 rounded-md border border-input bg-background px-3 py-2 text-base ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 md:text-sm"
                        type="text"
                        bind:value={captionText}
                        disabled={isSaving}
                        placeholder="Update caption"
                        use:preventViewerNavigation
                        data-testid="caption-input"
                        onclick={(e) => e.stopPropagation()}
                    />
                    <button
                        type="button"
                        class="inline-flex h-9 w-9 items-center justify-center rounded-md border border-primary bg-primary text-primary-foreground transition disabled:cursor-not-allowed disabled:border-input disabled:bg-background disabled:text-muted-foreground disabled:opacity-50"
                        onclick={(e) => {
                            e.stopPropagation();
                            saveCaption();
                        }}
                        disabled={!isDirty || isSaving}
                        aria-label="Save caption"
                        data-testid="save-caption-button"
                    >
                        <Check class="size-5" />
                    </button>
                    <button
                        type="button"
                        onclick={(e) => {
                            e.stopPropagation();
                            onDeleteCaption();
                        }}
                        data-testid="delete-caption-button"
                    >
                        <Trash2 class="size-6" />
                    </button>
                </div>
            {:else}
                <span class="text-sm">{caption.text}</span>
            {/if}
        </div>
        <div class="flex flex-wrap gap-1.5">
            <CaptionMatchScore metadataDict={caption.metadata_dict} />
            <CaptionRepetitionBadge metadataDict={caption.metadata_dict} />
        </div>
    </div>
</div>
