<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		children: Snippet;
		fullWidth?: boolean;
		onscroll?: (e: Event) => void;
		elementRef?: (el: HTMLDivElement) => void;
	}

	const {
		children,
		fullWidth = false,
		onscroll,
		elementRef
	}: Props = $props();

	let divElement: HTMLDivElement;

	$effect(() => {
		if (divElement && elementRef) {
			elementRef(divElement);
		}
	});

	function handleScroll(e: Event) {
		if (onscroll) {
			onscroll(e);
		}
	}
</script>

<div
	bind:this={divElement}
	class={`flex flex-col space-y-4 overflow-y-auto rounded-[1vw] bg-card p-4 ${fullWidth ? 'flex-1' : 'w-80'}`}
	onscroll={handleScroll}
>
	{@render children()}
</div>
