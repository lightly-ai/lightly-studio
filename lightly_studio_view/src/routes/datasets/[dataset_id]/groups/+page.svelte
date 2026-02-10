<script lang="ts">
    import type { Group } from '$lib/api/groups/+server';
    import type { ComponentGroup } from '../../api/component-groups/+server';
    import GroupSnapshot from '$lib/components/GroupSnapshot/GroupSnapshot.svelte';
    import Layout from '$lib/components/Layout/Layout.svelte';
    import LayoutSection from '$lib/components/Layout/LayoutSection.svelte';
    import SnapshotGrid from '$lib/components/Layout/SnapshotGrid.svelte';
    import type { Snippet } from 'svelte';
    import { goto } from '$app/navigation';
    import { page } from '$app/stores';
    import {
        encodePaginationHash,
        decodePaginationHash,
        encodeUrlState,
        decodeUrlState
    } from './url-state';
    import { browser } from '$app/environment';
    import { onMount } from 'svelte';

    const { data, children }: { data: any; children: Snippet } = $props();
    let groups = $state(data.initialGroups as Group[]);
    let hasMore = $state(data.hasMore as boolean);
    let total = $state(data.total as number);
    let isLoading = $state(false);
    let containerRef: HTMLDivElement | undefined;
    let initialLoadDone = $state(false);
    let hashHandled = $state(false);
    let componentGroups = $state<ComponentGroup[]>([]);
    let isLoadingGroups = $state(true);

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

        // Update URL hash with pagination and current scroll position
        updateUrlWithState();
    }

    function updateUrlWithState() {
        if (!containerRef) return;

        // Store the current loaded range
        const hash = encodeUrlState({
            pagination: {
                offset: 0, // Always load from beginning to reproduce exact state
                limit: groups.length // Current number of loaded items
            }
        });
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

    // Fetch component groups on mount
    onMount(async () => {
        try {
            const response = await fetch('/api/component-groups');
            const data = await response.json();
            componentGroups = data.componentGroups;
        } catch (error) {
            console.error('Failed to load component groups:', error);
        } finally {
            isLoadingGroups = false;
        }
    });

    // Handle hash-based pagination on mount
    $effect(() => {
        if (!browser || hashHandled) return;

        const hash = window.location.hash;
        if (hash && hash !== '#') {
            hashHandled = true;
            const urlState = decodeUrlState(hash);
            const offset = urlState.pagination?.offset || 0;
            const limit = urlState.pagination?.limit || 20;

            // Load exact range specified in hash to reproduce page state
            if (limit > groups.length) {
                const loadFromHash = async () => {
                    isLoading = true;
                    // Load the exact range: from offset to offset+limit
                    const response = await fetch(`/api/groups?offset=${offset}&limit=${limit}`);
                    const newData = await response.json();
                    groups = newData.groups;
                    hasMore = newData.hasMore;
                    total = newData.total;
                    isLoading = false;
                };
                loadFromHash();
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
    <LayoutSection>
        <div class="sidebar">
            <h3 class="sidebar-title">Component Groups</h3>
            {#if isLoadingGroups}
                <div class="loading-state">Loading...</div>
            {:else}
                <nav class="component-groups-menu">
                    {#each componentGroups as group (group.id)}
                        <button class="menu-item">
                            <span class="menu-icon">{group.icon}</span>
                            <span class="menu-label">{group.name}</span>
                            <span class="menu-count">{group.count}</span>
                        </button>
                    {/each}
                </nav>
            {/if}
        </div>
    </LayoutSection>
    <LayoutSection
        fullWidth
        elementRef={(el) => {
            containerRef = el;
        }}
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
</Layout>

<style>
    .sidebar {
        padding: 1rem;
        height: 100%;
    }

    .sidebar-title {
        font-size: 0.875rem;
        font-weight: 600;
        margin: 0 0 1rem 0;
        color: #ffffff;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .loading-state {
        color: #d1d5db;
        font-size: 0.875rem;
        padding: 1rem 0;
    }

    .component-groups-menu {
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
    }

    .menu-item {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.75rem;
        background: transparent;
        border: none;
        border-radius: 0.375rem;
        cursor: pointer;
        transition: background-color 0.15s;
        text-align: left;
        width: 100%;
    }

    .menu-item:hover {
        background-color: rgba(255, 255, 255, 0.1);
    }

    .menu-item:active {
        background-color: rgba(255, 255, 255, 0.15);
    }

    .menu-icon {
        font-size: 1.25rem;
        line-height: 1;
        flex-shrink: 0;
    }

    .menu-label {
        flex: 1;
        font-size: 0.875rem;
        font-weight: 500;
        color: #ffffff;
    }

    .menu-count {
        font-size: 0.75rem;
        font-weight: 600;
        color: #ffffff;
        background-color: rgba(255, 255, 255, 0.15);
        padding: 0.125rem 0.5rem;
        border-radius: 0.75rem;
        flex-shrink: 0;
    }

    .loading {
        display: flex;
        justify-content: center;
        padding: 1.5rem;
        color: #666;
        font-size: 0.875rem;
    }
</style>
