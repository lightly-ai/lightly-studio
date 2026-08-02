<script lang="ts">
	import { Progress as ProgressPrimitive, type WithoutChildrenOrChild } from "bits-ui";
	import { cn } from "$lib/utils/shadcn.js";

	let {
		ref = $bindable(null),
		value = 0,
		max = 100,
		class: className,
		...restProps
	}: WithoutChildrenOrChild<ProgressPrimitive.RootProps> = $props();
</script>

<ProgressPrimitive.Root
	bind:ref
	{value}
	{max}
	class={cn("bg-secondary relative h-2 w-full overflow-hidden rounded-full", className)}
	{...restProps}
>
	<div
		class="bg-primary h-full w-full flex-1 transition-transform duration-300 ease-out"
		style="transform: translateX(-{100 - ((value ?? 0) / (max || 1)) * 100}%)"
	></div>
</ProgressPrimitive.Root>
