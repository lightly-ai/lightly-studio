<script lang="ts">
    import { cn } from '$lib/utils/shadcn.js';
    import { Checkbox as CheckboxPrimitive, type WithoutChildrenOrChild } from 'bits-ui';

    let {
        ref = $bindable(null),
        checked = $bindable(false),
        indeterminate = $bindable(false),
        class: className,
        ...restProps
    }: WithoutChildrenOrChild<CheckboxPrimitive.RootProps> = $props();
</script>

<CheckboxPrimitive.Root
    bind:ref
    class={cn(
        'border-primary ring-offset-background focus-visible:ring-ring data-[state=checked]:bg-primary data-[state=checked]:text-primary-foreground peer box-content size-4 shrink-0 rounded-sm border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 data-[disabled=true]:cursor-not-allowed data-[disabled=true]:opacity-50',
        className
    )}
    bind:checked
    bind:indeterminate
    {...restProps}
>
    {#snippet children({ checked, indeterminate })}
        <div class="flex size-4 items-center justify-center text-current">
            {#if indeterminate}
                {#await import("@lucide/svelte/icons/minus") then { default: Minus }}
                    <Minus class="size-3.5" />
                {/await}
            {:else if checked}
                {#await import("@lucide/svelte/icons/check") then { default: Check }}
                    <Check class="size-3.5" />
                {/await}
            {:else}
                <div class="size-3.5" />
            {/if}
        </div>
    {/snippet}
</CheckboxPrimitive.Root>
