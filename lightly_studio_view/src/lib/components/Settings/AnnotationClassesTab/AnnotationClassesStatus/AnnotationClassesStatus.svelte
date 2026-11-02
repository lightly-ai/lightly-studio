<script lang="ts">
    interface Props {
        totalCount: number;
        visibleCount: number;
        searchText: string;
        exactMatchName?: string;
        isLoading: boolean;
    }

    const { totalCount, visibleCount, searchText, exactMatchName, isLoading }: Props = $props();
</script>

<!-- Empty while the classes load, because counts and matches are not known yet. The list
     shows the loading state, and min-h-4 keeps the layout still. -->
<p class="min-h-4 px-2 text-xs text-muted-foreground">
    {#if isLoading}
        <!-- Nothing to show yet. -->
    {:else if exactMatchName}
        <span class="font-medium text-foreground">{exactMatchName}</span>
        already exists.
    {:else if searchText && visibleCount === 0}
        No annotation class matches.
    {:else}
        {#if searchText}
            {visibleCount} of
        {/if}
        {totalCount} annotation {totalCount === 1 ? 'class' : 'classes'}
    {/if}
</p>
