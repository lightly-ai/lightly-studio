<script lang="ts">
    import { cn } from '$lib/utils/shadcn.js';
    import type { Snippet } from 'svelte';
    import type { HTMLAttributes } from 'svelte/elements';

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

    interface Props {
        variant?: TypographyVariant;
        component?: ComponentType;
        class?: string;
        children?: Snippet;
        props?: HTMLAttributes<HTMLElement>;
    }

    let { variant = 'body1', component, class: className, children, props }: Props = $props();

    // Auto-determine component if not provided
    const defaultComponent = $derived<ComponentType>(
        component ||
            (variant.startsWith('h') && ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'].includes(variant)
                ? (variant as ComponentType)
                : variant === 'caption' || variant === 'overline'
                  ? 'span'
                  : 'p')
    );

    const variantClasses: Record<TypographyVariant, string> = {
        h1: 'text-4xl font-bold leading-tight tracking-tight',
        h2: 'text-3xl font-semibold leading-tight tracking-tight',
        h3: 'text-2xl font-semibold leading-snug',
        h4: 'text-xl font-semibold leading-snug',
        h5: 'text-lg font-medium leading-normal',
        h6: 'text-base font-medium leading-normal',
        body1: 'text-base leading-normal',
        body2: 'text-sm leading-normal',
        caption: 'text-xs leading-tight',
        overline: 'text-xs font-medium uppercase leading-tight tracking-wider',
        subtitle1: 'text-base font-medium leading-normal',
        subtitle2: 'text-sm font-medium leading-normal'
    };

    const classes = $derived(cn(variantClasses[variant], className));
</script>

<svelte:element this={defaultComponent} class={classes} {...props}>
    {@render children?.()}
</svelte:element>
