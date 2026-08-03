<script lang="ts">
	import { cn } from "$lib/utils/shadcn.js";
	import { ContextMenu as ContextMenuPrimitive } from "bits-ui";
	import { ChevronRight } from "@lucide/svelte";

	let {
		ref = $bindable(null),
		class: className,
		inset,
		children,
		...restProps
	}: ContextMenuPrimitive.SubTriggerProps & {
		inset?: boolean;
	} = $props();
</script>

<ContextMenuPrimitive.SubTrigger
	bind:ref
	class={cn(
		"data-[highlighted]:bg-accent data-[highlighted]:text-accent-foreground data-[state=open]:bg-accent data-[state=open]:text-accent-foreground flex cursor-default select-none items-center gap-2 rounded-sm px-2 py-1.5 text-sm outline-none [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
		inset && "pl-8",
		className
	)}
	{...restProps}
>
	{@render children?.()}
	<ChevronRight class="ml-auto" />
</ContextMenuPrimitive.SubTrigger>
