<script lang="ts">
    import type { Group } from '$lib/api/groups/+server';
    import type { ComponentGroup } from '../../api/component-groups/+server';
    import type { ComponentWithGroup } from '../../api/components/+server';
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
    let selectedComponentType = $state<string | null>(null);
    let viewMode = $state<'groups' | 'components'>('groups');
    let components = $state<ComponentWithGroup[]>([]);
    let componentsHasMore = $state(false);
    let componentsTotal = $state(0);

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

    async function loadGroups(offset: number, limit: number, reset: boolean = false) {
        if (isLoading) return;

        isLoading = true;
        const params = new URLSearchParams({
            offset: offset.toString(),
            limit: limit.toString()
        });

        if (selectedComponentType) {
            params.set('component_type', selectedComponentType);
        }

        const response = await fetch(`/api/groups?${params}`);
        const newData = await response.json();

        if (reset) {
            groups = newData.groups;
        } else {
            groups = [...groups, ...newData.groups];
        }
        hasMore = newData.hasMore;
        total = newData.total;
        isLoading = false;

        if (!reset) {
            updateUrlWithState();
        }
    }

    async function loadComponents(offset: number, limit: number, reset: boolean = false) {
        if (isLoading) return;

        isLoading = true;
        const params = new URLSearchParams({
            offset: offset.toString(),
            limit: limit.toString()
        });

        if (selectedComponentType) {
            params.set('component_type', selectedComponentType);
        }

        const response = await fetch(`/api/components?${params}`);
        const newData = await response.json();

        if (reset) {
            components = newData.components;
        } else {
            components = [...components, ...newData.components];
        }
        componentsHasMore = newData.hasMore;
        componentsTotal = newData.total;
        isLoading = false;
    }

    async function loadMore() {
        if (isLoading) return;

        if (viewMode === 'groups') {
            if (!hasMore) return;
            const offset = groups.length;
            const itemsPerPage = calculateItemsPerPage();
            await loadGroups(offset, itemsPerPage, false);
        } else {
            if (!componentsHasMore) return;
            const offset = components.length;
            const itemsPerPage = calculateItemsPerPage();
            await loadComponents(offset, itemsPerPage, false);
        }
    }

    async function handleComponentTypeFilter(componentType: string | null) {
        selectedComponentType = componentType;
        viewMode = 'groups';
        const itemsPerPage = calculateItemsPerPage();
        await loadGroups(0, itemsPerPage, true);

        // Update URL hash with filter
        const hash = encodeUrlState({
            pagination: {
                offset: 0,
                limit: itemsPerPage
            },
            filters: {
                componentType: componentType || undefined
            }
        });
        const url = new URL($page.url);
        url.hash = hash;
        goto(url.toString(), { replaceState: true, noScroll: true, keepFocus: true });

        // Scroll to top
        if (containerRef) {
            containerRef.scrollTop = 0;
        }
    }

    async function handleComponentView(componentType: string) {
        selectedComponentType = componentType;
        viewMode = 'components';
        const itemsPerPage = calculateItemsPerPage();
        await loadComponents(0, itemsPerPage, true);

        // Update URL hash
        const hash = encodeUrlState({
            pagination: {
                offset: 0,
                limit: itemsPerPage
            },
            filters: {
                componentType
            },
            view: {
                viewMode: 'components'
            }
        });
        const url = new URL($page.url);
        url.hash = hash;
        goto(url.toString(), { replaceState: true, noScroll: true, keepFocus: true });

        // Scroll to top
        if (containerRef) {
            containerRef.scrollTop = 0;
        }
    }

    function updateUrlWithState() {
        if (!containerRef) return;

        // Store the current loaded range and filter state
        const hash = encodeUrlState({
            pagination: {
                offset: 0, // Always load from beginning to reproduce exact state
                limit: groups.length // Current number of loaded items
            },
            filters: {
                componentType: selectedComponentType || undefined
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

    // Handle hash-based pagination and filters on mount
    $effect(() => {
        if (!browser || hashHandled) return;

        const hash = window.location.hash;
        if (hash && hash !== '#') {
            hashHandled = true;
            const urlState = decodeUrlState(hash);
            const offset = urlState.pagination?.offset || 0;
            const limit = urlState.pagination?.limit || 20;
            const componentType = urlState.filters?.componentType;

            // Restore filter state
            if (componentType) {
                selectedComponentType = componentType;
            }

            // Load exact range specified in hash to reproduce page state
            if (limit > groups.length) {
                const loadFromHash = async () => {
                    isLoading = true;
                    const params = new URLSearchParams({
                        offset: offset.toString(),
                        limit: limit.toString()
                    });

                    if (componentType) {
                        params.set('component_type', componentType);
                    }

                    const response = await fetch(`/api/groups?${params}`);
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
            <section class="sidebar-section">
                <h3 class="sidebar-title">Component Groups</h3>
                {#if isLoadingGroups}
                    <div class="loading-state">Loading...</div>
                {:else}
                    <nav class="component-groups-menu">
                        {#each componentGroups as group (group.id)}
                            <button
                                class="menu-item"
                                class:active={selectedComponentType === group.id && viewMode === 'components'}
                                onclick={() => handleComponentView(group.id)}
                            >
                                <span class="menu-icon">{group.icon}</span>
                                <span class="menu-label">{group.name}</span>
                                <span class="menu-count">{group.count}</span>
                            </button>
                        {/each}
                    </nav>
                {/if}
            </section>
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
        {#if selectedComponentType}
            <div class="filter-indicator">
                Showing all "{componentGroups.find((g) => g.id === selectedComponentType)?.name ||
                    selectedComponentType}" components ({componentsTotal} components)
            </div>
            <SnapshotGrid>
                {#each components as component (component.component_id)}
                    <div class="component-card">
                        <img
                            src={component.thumbnail_url}
                            alt={component.component_name}
                            class="component-image"
                        />
                        <div class="component-info">
                            <div class="component-name">{component.component_name}</div>
                            <div class="component-group-name">{component.group_name}</div>
                        </div>
                    </div>
                {/each}
            </SnapshotGrid>
        {:else}
            <SnapshotGrid>
                {#each groups as group (group.group_id)}
                    <GroupSnapshot {group} />
                {/each}
            </SnapshotGrid>
        {/if}
    </LayoutSection>
</Layout>

<style>
    .sidebar {
        padding: 1rem;
        height: 100%;
        display: flex;
        flex-direction: column;
        gap: 1.5rem;
    }

    .sidebar-section {
        flex-shrink: 0;
    }

    .sidebar-divider {
        height: 1px;
        background-color: rgba(255, 255, 255, 0.1);
        margin: 0.5rem 0;
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

    .menu-item.active {
        background-color: rgba(255, 255, 255, 0.2);
        border-left: 3px solid #60a5fa;
    }

    .menu-item.clear-filter {
        background-color: rgba(239, 68, 68, 0.1);
        border-left: 3px solid #ef4444;
        margin-bottom: 0.5rem;
    }

    .menu-item.clear-filter:hover {
        background-color: rgba(239, 68, 68, 0.2);
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

    .filter-indicator {
        padding: 0.75rem 1rem;
        background-color: rgba(96, 165, 250, 0.1);
        border-left: 3px solid #60a5fa;
        color: #ffffff;
        font-size: 0.875rem;
        margin-bottom: 1rem;
    }

    .component-card {
        display: flex;
        flex-direction: column;
        background-color: rgba(255, 255, 255, 0.05);
        border-radius: 0.5rem;
        overflow: hidden;
        cursor: pointer;
        transition: transform 0.15s, background-color 0.15s;
    }

    .component-card:hover {
        transform: translateY(-2px);
        background-color: rgba(255, 255, 255, 0.08);
    }

    .component-image {
        width: 100%;
        height: 180px;
        object-fit: cover;
    }

    .component-info {
        padding: 0.75rem;
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
    }

    .component-name {
        font-size: 0.875rem;
        font-weight: 500;
        color: #ffffff;
    }

    .component-group-name {
        font-size: 0.75rem;
        color: #9ca3af;
    }

    .loading {
        display: flex;
        justify-content: center;
        padding: 1.5rem;
        color: #666;
        font-size: 0.875rem;
    }
</style>
