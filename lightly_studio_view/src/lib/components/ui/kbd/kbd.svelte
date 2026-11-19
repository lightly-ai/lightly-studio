<script lang="ts">
	import type { HTMLAttributes } from "svelte/elements";
	import { cn } from "$lib/utils/shadcn.js";

	let { class: className, children, ...restProps }: HTMLAttributes<HTMLElement> = $props();
</script>

<kbd
	class={cn(
		"bg-muted text-foreground inline-flex h-4 min-w-4 items-center justify-center rounded border px-1 font-mono text-[10px] font-medium leading-none",
		className
	)}
	{...restProps}
>
	{@render children?.()}
</kbd>
