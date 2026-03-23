<script lang="ts" generics="T">
    import type { Snippet } from 'svelte';
    import type { CreateQueryResult } from '@tanstack/svelte-query';

    type Props<T> = {
        query: CreateQueryResult<T, Error>;
        children: Snippet<[T]>;
        loading?: Snippet;
        error?: Snippet<[Error]>;
    };

    // eslint-disable-next-line no-undef
    let { query, children, loading, error }: Props<T> = $props();
</script>

{#if $query.isLoading}
    {#if loading}
        {@render loading()}
    {:else}
        Loading...
    {/if}
{:else if $query.isError}
    {#if error}
        {@render error($query.error)}
    {:else}
        Error: {$query.error.message}
    {/if}
{:else if $query.data}
    {@render children($query.data)}
{/if}
