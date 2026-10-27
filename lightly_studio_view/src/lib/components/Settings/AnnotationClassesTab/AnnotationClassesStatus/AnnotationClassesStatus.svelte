<script lang="ts">
    interface Props {
        totalCount: number;
        visibleCount: number;
        searchText: string;
        exactMatchName?: string;
    }

    const { totalCount, visibleCount, searchText, exactMatchName }: Props = $props();
</script>

<p class="px-2 text-xs text-muted-foreground">Changes to annotation classes save immediately.</p>
<p class="px-2 text-xs text-muted-foreground">
    {#if exactMatchName}
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
