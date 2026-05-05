<script lang="ts">
    import type { Snippet } from 'svelte';
    import { LazyTrigger } from '$lib/components/LazyTrigger';
    import Spinner from '$lib/components/Spinner/Spinner.svelte';

    type GridContainerMessage = {
        loading?: string;
        error?: string;
        empty?: {
            title?: string;
            description?: string;
        };
    };

    type GridContainerStatus = {
        loading: boolean;
        error: boolean;
        empty: boolean;
        success: boolean;
    };

    type GridContainerLoader = {
        loadMore?: () => void;
        disabled?: boolean;
        loading?: boolean;
    };

    const DEFAULT_MESSAGE = {
        loading: 'Loading items...',
        error: 'Something went wrong.',
        empty: {
            title: 'No items found',
            description: 'There are no items to display.'
        }
    } as const;

    let {
        status,
        message,
        loader,
        itemCount = 0,
        children
    }: {
        status: GridContainerStatus;
        message?: GridContainerMessage;
        loader?: GridContainerLoader;
        itemCount?: number;
        children?: Snippet<
            [
                {
                    footer: Snippet;
                }
            ]
        >;
    } = $props();

    const resolvedMessage = $derived.by(() => ({
        loading: message?.loading ?? DEFAULT_MESSAGE.loading,
        error: message?.error ?? DEFAULT_MESSAGE.error,
        empty: {
            title: message?.empty?.title ?? DEFAULT_MESSAGE.empty.title,
            description: message?.empty?.description ?? DEFAULT_MESSAGE.empty.description
        }
    }));

    const resolvedLoader = $derived.by(() => ({
        loadMore: loader?.loadMore ?? (() => undefined),
        disabled: loader?.disabled ?? true,
        loading: loader?.loading ?? false
    }));
</script>

{#snippet footer()}
    {#key itemCount}
        <LazyTrigger onIntersect={resolvedLoader.loadMore} disabled={resolvedLoader.disabled} />
    {/key}
    {#if resolvedLoader.loading}
        <div class="flex justify-center p-4" data-testid="grid-container-fetching-next-page">
            <Spinner />
        </div>
    {/if}
{/snippet}

{#if status.loading}
    <div class="flex h-full w-full items-center justify-center gap-2">
        <Spinner />
        <div>{resolvedMessage.loading}</div>
    </div>
{:else if status.error}
    <div class="flex h-full w-full items-center justify-center">
        <div class="text-center text-muted-foreground">{resolvedMessage.error}</div>
    </div>
{:else if status.empty}
    <div class="flex h-full w-full items-center justify-center">
        <div class="text-center text-muted-foreground">
            <div class="mb-2 text-lg font-medium">{resolvedMessage.empty.title}</div>
            <div class="text-sm">{resolvedMessage.empty.description}</div>
        </div>
    </div>
{:else if status.success}
    {@render children?.({ footer })}
{/if}
