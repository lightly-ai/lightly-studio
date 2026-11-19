<script lang="ts">
	import type { HTMLAnchorAttributes } from "svelte/elements";
	import type { Snippet } from "svelte";
	import type { WithElementRef } from "bits-ui";
	import { cn } from "$lib/utils/shadcn.js";

	let {
		ref = $bindable(null),
		class: className,
		href = undefined,
		child,
		children,
		...restProps
	}: WithElementRef<HTMLAnchorAttributes> & {
		child?: Snippet<[{ props: HTMLAnchorAttributes }]>;
	} = $props();

	const attrs = $derived({
		class: cn("hover:text-foreground transition-colors", className),
		href,
		...restProps,
	});
</script>

{#if child}
	{@render child({ props: attrs })}
{:else if !href}
	<!-- A crumb the user may not follow. Without href the anchor is not a link and not
	     focusable; it shows as dimmed text with no hover. -->
	<a
		bind:this={ref}
		{...restProps}
		aria-disabled="true"
		class={cn("cursor-default opacity-60", className)}
	>
		{@render children?.()}
	</a>
{:else}
	<a bind:this={ref} {...attrs}>
		{@render children?.()}
	</a>
{/if}
