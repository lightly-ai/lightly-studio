<script lang="ts">
    import { cn } from '$lib/utils/shadcn.js';
    import { Switch as SwitchPrimitive } from 'bits-ui';

    let {
        ref = $bindable(null),
        checked = $bindable(false),
        class: className = '',
        ...restProps
    } = $props();
</script>

<SwitchPrimitive.Root
    bind:ref
    bind:checked
    class={cn(
        'focus-visible:ring-ring focus-visible:ring-offset-background data-[state=checked]:bg-primary data-[state=unchecked]:bg-input peer inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
        className
    )}
    {...restProps}
>
    <SwitchPrimitive.Thumb
        class={cn(
            'bg-background pointer-events-none block h-4 w-4 rounded-full shadow-lg ring-0 transition-transform data-[state=checked]:translate-x-4 data-[state=unchecked]:translate-x-0'
        )}
    />
</SwitchPrimitive.Root>
