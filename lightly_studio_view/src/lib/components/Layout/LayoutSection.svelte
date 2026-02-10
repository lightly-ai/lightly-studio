<script lang="ts">
	import type { Snippet } from 'svelte';

	const {
		children,
		fullWidth = false,
		onscroll
	}: { children: Snippet; fullWidth?: boolean; onscroll?: (e: Event) => void } = $props();

	function handleScroll(e: Event) {
		if (onscroll) {
			onscroll(e);
		}
	}
</script>

<div
	class={`flex flex-col space-y-4 overflow-y-auto rounded-[1vw] bg-card p-4 ${fullWidth ? 'flex-1' : 'w-80'}`}
	onscroll={handleScroll}
>
	{@render children()}
</div>
