<script lang="ts">
    import { ChevronDown, Search } from '@lucide/svelte';
    import { Button } from '$lib/components';

    /**
     * Fast-filter strip above the working area: annotation class, camera and frame-range filters
     * plus a free-text filter. Placeholders until the annotation/frame queries land, so the
     * controls are disabled rather than wired to no-op handlers.
     */
    const filters = ['Annotation class', 'Annotation source', 'Camera', 'Frame range'];
</script>

<div
    class="flex h-11 shrink-0 items-center gap-2 border-b bg-background px-3"
    data-testid="workspace-filter-bar"
>
    <div class="relative w-56 shrink-0">
        <Search
            class="pointer-events-none absolute left-2 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden="true"
        />
        <input
            type="text"
            disabled
            placeholder="Filter annotations…"
            aria-label="Filter annotations"
            class="h-8 w-full rounded-md border bg-muted/40 pl-8 pr-2 text-sm placeholder:text-muted-foreground disabled:cursor-not-allowed"
        />
    </div>
    <div class="flex min-w-0 items-center gap-1 overflow-x-auto">
        {#each filters as filter (filter)}
            <Button
                variant="outline"
                iconAfter={ChevronDown}
                buttonProps={{
                    disabled: true,
                    size: 'sm',
                    class: 'h-8 shrink-0 gap-1 text-xs',
                    title: `${filter} (coming soon)`
                }}
            >
                {filter}
            </Button>
        {/each}
    </div>
</div>
