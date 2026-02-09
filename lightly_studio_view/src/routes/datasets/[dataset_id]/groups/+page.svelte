<script lang="ts">
    import type { Group } from '$lib/api/groups/+server';

    const { data } = $props();
    const { groups, total } = data as { groups: Group[]; total: number };
</script>

<div class="groups-container">
    <header>
        <h1>Groups</h1>
        <p class="subtitle">Total: {total}</p>
    </header>

    <div class="groups-grid">
        {#each groups as group (group.group_id)}
            <div class="group-card">
                {#if group.components[0]?.thumbnail_url}
                    <div class="thumbnail">
                        <img src={group.components[0].thumbnail_url} alt={group.group_name} />
                        <span class="component-count">+{group.components.length}</span>
                    </div>
                {/if}
            </div>
        {/each}
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

    .group-card {
        background: white;
        transition: all 0.2s;
        overflow: hidden;
        cursor: pointer;
        border: none;
        border-radius: 0;
    }

    .group-card:hover {
        transform: scale(1.02);
        z-index: 1;
    }

    .thumbnail {
        position: relative;
        width: 100%;
        aspect-ratio: 4 / 3;
        overflow: hidden;
        background: #f3f4f6;
    }

    .thumbnail img {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }

    .component-count {
        position: absolute;
        bottom: 0.75rem;
        right: 0.75rem;
        background: rgba(0, 0, 0, 0.6);
        color: white;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        font-size: 0.875rem;
        font-weight: 500;
    }

    .group-info {
        padding: 1rem;
    }

    .group-card h2 {
        font-size: 1rem;
        font-weight: 600;
        margin: 0 0 0.5rem 0;
    }

    .created {
        font-size: 0.75rem;
        color: #9ca3af;
    }
</style>
