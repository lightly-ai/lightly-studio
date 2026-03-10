<script lang="ts">
    import type { HTMLAttributes } from 'svelte/elements';
    import Typography from './Typography.svelte';
    import type { ComponentType, TypographyVariant } from './constants';

    let {
        variant,
        component,
        className,
        props
    }: {
        variant?: TypographyVariant;
        component?: ComponentType;
        className?: string;
        props?: HTMLAttributes<HTMLElement>;
    } = $props();
</script>

<Typography {variant} {component} {className} {props}>Test Content</Typography>
