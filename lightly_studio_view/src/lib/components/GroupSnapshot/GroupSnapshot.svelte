<script lang="ts">
	import type { Group } from '$lib/api/groups/+server';

	interface Props {
		group: Group;
	}

	const { group }: Props = $props();
</script>

<div class="group-card">
	{#if group.thumbnail_url}
		<div class="thumbnail">
			<img src={group.thumbnail_url} alt={group.group_name} />
			<span class="component-count">+{group.components.length}</span>
		</div>
	{/if}
</div>

<style>
	.group-card {
		background: white;
		overflow: hidden;
		cursor: pointer;
		border: none;
		border-radius: 0;
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
		transition: transform 0.2s;
	}

	.group-card:hover .thumbnail img {
		transform: scale(1.1);
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
</style>
