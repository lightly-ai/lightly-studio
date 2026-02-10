<script lang="ts">
    import type { Group } from '$lib/api/groups/+server';
    import GroupSnapshot from '$lib/components/GroupSnapshot/GroupSnapshot.svelte';
    import Layout from '$lib/components/Layout/Layout.svelte';
    import LayoutSection from '$lib/components/Layout/LayoutSection.svelte';
    import SnapshotGrid from '$lib/components/Layout/SnapshotGrid.svelte';
    import type { Snippet } from 'svelte';
    import { goto } from '$app/navigation';
    import { page } from '$app/stores';
    import { encodePaginationHash, decodePaginationHash } from './pagination-utils';
    import { browser } from '$app/environment';

    const { data, children }: { data: any; children: Snippet } = $props();
    let groups = $state(data.initialGroups as Group[]);
    let hasMore = $state(data.hasMore as boolean);
    let total = $state(data.total as number);
    let isLoading = $state(false);
    let containerRef: HTMLDivElement | undefined;
    let initialLoadDone = $state(false);
    let hashHandled = $state(false);

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

        // Update URL hash with new pagination state
        const hash = encodePaginationHash({ offset, limit: itemsPerPage });
        const url = new URL($page.url);
        url.hash = hash;
        goto(url.toString(), { replaceState: true, noScroll: true, keepFocus: true });
    }

    function handleScroll(element: HTMLDivElement) {
        containerRef = element;
        if (isLoading || !hasMore) return;

        const { scrollTop, scrollHeight, clientHeight } = element;
        // Start loading when user has scrolled 70% of the way down
        const scrollPercentage = (scrollTop + clientHeight) / scrollHeight;

        if (scrollPercentage >= 0.7) {
            loadMore();
        }
    }

    // Handle hash-based pagination on mount
    $effect(() => {
        if (!browser || hashHandled) return;

        const hash = window.location.hash;
        if (hash && hash !== '#') {
            hashHandled = true;
            const { offset } = decodePaginationHash(hash);

            // If hash indicates we should load more items beyond initial load
            if (offset > 0 && groups.length < offset) {
                const loadToOffset = async () => {
                    isLoading = true;
                    const response = await fetch(`/api/groups?offset=0&limit=${offset + 20}`);
                    const newData = await response.json();
                    groups = newData.groups;
                    hasMore = newData.hasMore;
                    total = newData.total;
                    isLoading = false;
                };
                loadToOffset();
            }
        } else {
            hashHandled = true;
        }
    });

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
    });
</script>

<Layout>
    <LayoutSection>Column 1</LayoutSection>
    <LayoutSection
        fullWidth
        onscroll={(e) => {
            const element = e.currentTarget as HTMLDivElement;
            handleScroll(element);
        }}
    >
        <SnapshotGrid>
            {#each groups as group (group.group_id)}
                <GroupSnapshot {group} />
            {/each}
        </SnapshotGrid>
    </LayoutSection>
    <LayoutSection>Column 2</LayoutSection>
</Layout>

<style>
    .loading {
        display: flex;
        justify-content: center;
        padding: 1.5rem;
        color: #666;
        font-size: 0.875rem;
    }
</style>
