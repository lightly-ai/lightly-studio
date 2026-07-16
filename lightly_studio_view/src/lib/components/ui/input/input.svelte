<script lang="ts">
	import type { HTMLInputAttributes, HTMLInputTypeAttribute } from "svelte/elements";
	import type { WithElementRef } from "bits-ui";
	import { cn } from "$lib/utils/shadcn.js";

	type InputType = Exclude<HTMLInputTypeAttribute, "file">;

	type BaseProps = WithElementRef<
		Omit<HTMLInputAttributes, "type"> &
			({ type: "file"; files?: FileList } | { type?: InputType; files?: undefined })
	>;

	type Props = BaseProps & {
		/**
		 * When true, disables the input and shows an indeterminate linear
		 * progress bar at the bottom, consistent with Button.isPending.
		 */
		isPending?: boolean;
		/**
		 * Classes applied to the outer wrapper div (e.g. layout classes like flex-1).
		 * Use this instead of `class` when you need to control how the component
		 * participates in a flex/grid layout.
		 */
		wrapperClass?: string;
	};

	let {
		ref = $bindable(null),
		value = $bindable(),
		type,
		files = $bindable(),
		class: className,
		wrapperClass,
		isPending = false,
		disabled,
		...restProps
	}: Props = $props();

	const inputClass = $derived(
		cn(
			"border-input bg-background ring-offset-background placeholder:text-muted-foreground focus-visible:ring-ring flex h-10 w-full rounded-md border px-3 py-2 text-base file:border-0 file:bg-transparent file:text-sm file:font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 md:text-sm",
			className
		)
	);
</script>

<div class={cn("relative w-full", isPending && "overflow-hidden rounded-md", wrapperClass)}>
	{#if type === "file"}
		<input
			bind:this={ref}
			class={inputClass}
			type="file"
			bind:files
			disabled={isPending || disabled}
			{...restProps}
		/>
	{:else}
		<input
			bind:this={ref}
			class={inputClass}
			{type}
			bind:value
			disabled={isPending || disabled}
			{...restProps}
		/>
	{/if}
	{#if isPending}
		<span
			data-testid="input-progress"
			role="progressbar"
			aria-label="Loading"
			class="bg-current/20 pointer-events-none absolute inset-x-0 bottom-0 h-0.5 overflow-hidden"
		>
			<span class="input-progress-indicator absolute inset-y-0 bg-current"></span>
		</span>
	{/if}
</div>

<style>
	.input-progress-indicator {
		animation: input-progress-slide 1.2s ease-in-out infinite;
	}
	@keyframes input-progress-slide {
		0% {
			left: -40%;
			width: 40%;
		}
		50% {
			left: 30%;
			width: 55%;
		}
		100% {
			left: 100%;
			width: 40%;
		}
	}
</style>
