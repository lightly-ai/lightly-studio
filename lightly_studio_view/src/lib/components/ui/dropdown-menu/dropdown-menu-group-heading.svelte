<script lang="ts">
    import { DropdownMenu as DropdownMenuPrimitive } from 'bits-ui';
    import { cn } from '$lib/utils/shadcn.js';

    let {
        ref = $bindable(null),
        class: className,
        ...restProps
    }: DropdownMenuPrimitive.GroupHeadingProps = $props();
</script>

<DropdownMenuPrimitive.GroupHeading
    bind:ref
    class={cn('px-2 py-1.5 text-xs font-medium text-muted-foreground', className)}
    {...restProps}
/>
