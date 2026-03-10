<script lang="ts">
    import type { HTMLAttributes } from 'svelte/elements';
    import Typography from './Typography.svelte';

    type TypographyVariant =
        | 'h1'
        | 'h2'
        | 'h3'
        | 'h4'
        | 'h5'
        | 'h6'
        | 'body1'
        | 'body2'
        | 'caption'
        | 'overline'
        | 'subtitle1'
        | 'subtitle2';

    type ComponentType = 'h1' | 'h2' | 'h3' | 'h4' | 'h5' | 'h6' | 'p' | 'span' | 'div';

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

<Typography {variant} {component} class={className} {props}>Test Content</Typography>
