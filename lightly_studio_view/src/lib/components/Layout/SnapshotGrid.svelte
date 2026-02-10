<script lang="ts">
	import type { Snippet } from 'svelte';

	const { children }: { children: Snippet } = $props();
</script>

<div class="grid auto-rows-max gap-4" style="grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));">
	{@render children()}
</div>
