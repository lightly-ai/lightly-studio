<script lang="ts">
    import type { Group } from '$lib/api/groups/+server';
    import GroupSnapshot from '$lib/components/GroupSnapshot/GroupSnapshot.svelte';

    const { data } = $props();
    let groups = $state(data.initialGroups as Group[]);
    let hasMore = $state(data.hasMore as boolean);
    let total = $state(data.total as number);
    let isLoading = $state(false);
    let containerRef: HTMLDivElement;
    let initialLoadDone = $state(false);

    function calculateItemsPerPage(): number {
        if (!containerRef) return 10;

        const containerWidth = containerRef.clientWidth;
        const containerHeight = containerRef.clientHeight;

        const minItemWidth = 280;
        const itemHeight = 200; // Approximate height of GroupSnapshot
        const gap = 1;

        const columns = Math.floor(containerWidth / (minItemWidth + gap));
        const rows = Math.ceil(containerHeight / (itemHeight + gap));

        return Math.max(columns * rows, 10);
    }

    async function loadMore() {
        if (isLoading || !hasMore) return;

        isLoading = true;
        const offset = groups.length;
        const itemsPerPage = calculateItemsPerPage();
        const response = await fetch(`/api/groups?offset=${offset}&limit=${itemsPerPage}`);
        const newData = await response.json();

        groups = [...groups, ...newData.groups];
        hasMore = newData.hasMore;
        total = newData.total;
        isLoading = false;
    }

    function handleScroll() {
        if (!containerRef || isLoading || !hasMore) return;

        const { scrollTop, scrollHeight, clientHeight } = containerRef;
        const scrollThreshold = 200;

        if (scrollTop + clientHeight >= scrollHeight - scrollThreshold) {
            loadMore();
        }
    }

    $effect(() => {
        if (!containerRef) return;

        // Load additional page on mount if needed
        if (!initialLoadDone) {
            initialLoadDone = true;
            const itemsPerPage = calculateItemsPerPage();
            const currentItems = groups.length;

            // If we have less than 2 pages worth of items, load more
            if (currentItems < itemsPerPage * 2 && hasMore) {
                loadMore();
            }
        }

        containerRef.addEventListener('scroll', handleScroll);
        return () => containerRef.removeEventListener('scroll', handleScroll);
    });
</script>

<div class="groups-container" bind:this={containerRef}>
    <header>
        <h1>Groups</h1>
        <p class="subtitle">Total: {total}</p>
    </header>

    <div class="groups-grid">
        {#each groups as group (group.group_id)}
            <GroupSnapshot {group} />
        {/each}
    </div>

    {#if isLoading}
        <div class="loading">
            <p>Loading more groups...</p>
        </div>
    {/if}
</div>

<style>
    .groups-container {
        padding: 0;
        width: 100%;
        height: 100%;
        overflow-y: auto;
    }

    header {
        padding: 1.5rem;
        margin-bottom: 0;
        border-bottom: 1px solid #e5e7eb;
    }

    h1 {
        font-size: 1.5rem;
        font-weight: 600;
        margin-bottom: 0.25rem;
    }

    .subtitle {
        color: #666;
        font-size: 0.875rem;
    }

    .groups-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
        gap: 1px;
        background: #e5e7eb;
    }

    .loading {
        display: flex;
        justify-content: center;
        padding: 1.5rem;
        color: #666;
        font-size: 0.875rem;
    }
</style>
