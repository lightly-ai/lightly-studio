<script lang="ts">
    import type { Group } from '$lib/api/groups/+server';
    import GroupSnapshot from '$lib/components/GroupSnapshot/GroupSnapshot.svelte';
    import { goto } from '$app/navigation';
    import { encodePaginationState, type PaginationState } from '$lib/utils/pagination';

    const { data } = $props();
    const { groups, total, state, totalPages } = data as {
        groups: Group[];
        total: number;
        state: PaginationState;
        totalPages: number;
    };

    const currentPage = $derived(state.page || 1);

    function updateState(newState: PaginationState) {
        const token = encodePaginationState(newState);
        goto(`?state=${token}`);
    }

    function goToPage(page: number) {
        updateState({ ...state, page });
    }

    function previousPage() {
        if (currentPage > 1) {
            goToPage(currentPage - 1);
        }
    }
§
    function nextPage() {
        if (currentPage < totalPages) {
            goToPage(currentPage + 1);
        }
    }
</script>

<div class="groups-container">
    <header>
        <h1>Groups</h1>
        <p class="subtitle">Total: {total}</p>
    </header>

    <div class="groups-grid">
        {#each groups as group (group.group_id)}
            <GroupSnapshot {group} />
        {/each}
    </div>

    <div class="pagination">
        <button onclick={previousPage} disabled={currentPage === 1}>Previous</button>
        <span class="page-info">
            Page {currentPage} of {totalPages}
        </span>
        <button onclick={nextPage} disabled={currentPage === totalPages}>Next</button>
    </div>
</div>

<style>
    .groups-container {
        padding: 0;
        width: 100%;
        height: 100%;
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

    .pagination {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 1rem;
        padding: 1.5rem;
        border-top: 1px solid #e5e7eb;
    }

    .pagination button {
        padding: 0.5rem 1rem;
        background: white;
        border: 1px solid #d1d5db;
        border-radius: 4px;
        cursor: pointer;
        font-size: 0.875rem;
        transition: all 0.2s;
    }

    .pagination button:hover:not(:disabled) {
        background: #f9fafb;
        border-color: #9ca3af;
    }

    .pagination button:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }

    .page-info {
        font-size: 0.875rem;
        color: #666;
    }
</style>
