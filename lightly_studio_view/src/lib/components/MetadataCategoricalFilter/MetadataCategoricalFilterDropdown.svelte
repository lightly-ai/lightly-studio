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

<div class="mt-2 flex items-center gap-2" data-testid="metadata-categorical-filter">
    <span class="w-[100px] shrink-0 truncate text-xs text-muted-foreground" title={fieldLabel}
        >{fieldLabel}</span
    >
    <Popover.Root {onOpenChange}>
        <Popover.Trigger>
            {#snippet child({ props })}
                <Button
                    variant="outline"
                    buttonProps={{
                        ...props,
                        size: 'sm',
                        class: 'h-8 min-w-0 flex-1 justify-between px-3 text-xs font-normal max-sm:min-h-11',
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
        <Popover.Content class="w-[min(320px,calc(100vw-2rem))] p-2" align="end">
            {@render children()}
        </Popover.Content>
    </Popover.Root>
    {#if updating}
        <span class="shrink-0 text-xs text-muted-foreground" role="status">Updating…</span>
    {/if}
    {#if onRemove}
        <IconButton
            variant="ghost"
            size="icon"
            class="size-6 shrink-0"
            aria-label={`Remove metadata field ${fieldLabel}`}
            onclick={onRemove}
        >
            <X class="size-4" />
        </IconButton>
    {/if}
</div>
