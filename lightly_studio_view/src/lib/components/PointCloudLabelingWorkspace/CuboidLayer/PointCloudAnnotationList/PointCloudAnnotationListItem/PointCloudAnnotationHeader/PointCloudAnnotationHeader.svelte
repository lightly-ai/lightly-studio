<script lang="ts">
    import { ChevronDown, Trash2 } from '@lucide/svelte';
    import PointCloudAnnotationLabel from '$lib/components/PointCloudLabelingWorkspace/CuboidLayer/PointCloudAnnotationDetails/PointCloudAnnotationLabel';
    import { Typography } from '$lib/components/Typography';
    import { Tooltip } from '$lib/components/ui/tooltip';
    import { Button } from '$lib/components/ui/button';
    import { cn } from '$lib/utils';

    interface Props {
        collectionId: string;
        color: string;
        className: string;
        isSelected: boolean;
        editable: boolean;
        onToggle: () => void;
        onLabelChange?: (className: string) => void;
        onDelete?: () => void;
    }

    let {
        collectionId,
        color,
        className,
        isSelected,
        editable,
        onToggle,
        onLabelChange,
        onDelete
    }: Props = $props();
</script>

{#snippet colorSwatch()}
    <span class="size-3 shrink-0 rounded-sm" style="background-color: {color}" aria-hidden="true"
    ></span>
{/snippet}

<div class="flex w-full items-center">
    {#if editable}
        <div class="relative flex min-w-0 flex-1 items-center gap-2 px-4 py-2">
            <Button
                type="button"
                variant="ghost"
                class="absolute inset-0 h-full w-full rounded-none p-0 hover:bg-transparent"
                onclick={onToggle}
                aria-expanded={isSelected}
                aria-label="Toggle annotation details"
                data-testid="point-cloud-annotation-list-row"
            />
            {@render colorSwatch()}
            <div class="pointer-events-auto relative min-w-0 flex-1">
                <PointCloudAnnotationLabel
                    {collectionId}
                    currentLabel={className}
                    onSelect={(className) => onLabelChange?.(className)}
                />
            </div>
        </div>
    {:else}
        <button
            type="button"
            class="flex min-w-0 flex-1 items-center gap-2 px-4 py-3 text-left"
            onclick={onToggle}
            aria-expanded={isSelected}
            data-testid="point-cloud-annotation-list-row"
        >
            {@render colorSwatch()}
            <Typography variant="body2" className="flex-1 truncate">{className}</Typography>
        </button>
    {/if}
    {#if onDelete}
        <Tooltip content="Delete annotation">
            <Button
                variant="ghost"
                size="icon"
                class="p-2 text-muted-foreground hover:text-destructive"
                onclick={onDelete}
                aria-label="Delete annotation"
                data-testid="point-cloud-annotation-delete-button"
            >
                <Trash2 class="size-4 shrink-0" />
            </Button>
        </Tooltip>
    {/if}
    <button
        type="button"
        class="px-4 py-3"
        onclick={onToggle}
        aria-expanded={isSelected}
        aria-label="Toggle annotation details"
    >
        <ChevronDown
            class={cn(
                'size-4 shrink-0 text-muted-foreground transition-transform',
                isSelected && 'rotate-180'
            )}
        />
    </button>
</div>
