<script lang="ts">
    import { ChevronsUpDown, X } from '@lucide/svelte';
    import { Button } from '$lib/components';
    import { Button as IconButton } from '$lib/components/ui/button';
    import * as Popover from '$lib/components/ui/popover';
    import type { Snippet } from 'svelte';

    interface Props {
        fieldLabel: string;
        summary: string;
        disabled: boolean;
        loading: boolean;
        updating: boolean;
        onRemove?: () => void;
        onOpenChange: (open: boolean) => void;
        children: Snippet;
    }

    const {
        fieldLabel,
        summary,
        disabled,
        loading,
        updating,
        onRemove,
        onOpenChange,
        children
    }: Props = $props();
</script>

<div class="rounded-md border border-input bg-background" data-testid="metadata-categorical-filter">
    <div class="flex items-center justify-between gap-2 border-b px-3 py-2">
        <h3 class="min-w-0 truncate text-sm font-medium" title={fieldLabel}>{fieldLabel}</h3>
        <div class="flex shrink-0 items-center gap-1">
            {#if updating}
                <span class="text-xs text-muted-foreground" role="status">Updating…</span>
            {/if}
            {#if onRemove}
                <IconButton
                    variant="ghost"
                    size="icon"
                    class="size-6"
                    aria-label={`Remove metadata field ${fieldLabel}`}
                    onclick={onRemove}
                >
                    <X class="size-4" />
                </IconButton>
            {/if}
        </div>
    </div>
    <div class="p-2">
        <Popover.Root {onOpenChange}>
            <Popover.Trigger>
                {#snippet child({ props })}
                    <Button
                        variant="outline"
                        buttonProps={{
                            ...props,
                            size: 'sm',
                            class: 'h-8 w-full justify-between px-3 text-xs font-normal max-sm:min-h-11',
                            disabled,
                            'data-testid': 'metadata-categorical-filter-trigger'
                        }}
                        ariaLabel="Select metadata values"
                    >
                        <span class="truncate">{loading ? 'Loading…' : summary}</span>
                        <ChevronsUpDown class="opacity-50" />
                    </Button>
                {/snippet}
            </Popover.Trigger>
            <Popover.Content class="w-[min(320px,calc(100vw-2rem))] p-2" align="start">
                {@render children()}
            </Popover.Content>
        </Popover.Root>
    </div>
</div>
