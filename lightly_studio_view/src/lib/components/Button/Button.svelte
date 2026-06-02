<script lang="ts">
    import type { Component, Snippet } from 'svelte';
    import type { IconProps } from '@lucide/svelte';
    import {
        Button as UiButton,
        type ButtonProps,
        type ButtonVariant
    } from '$lib/components/ui/button';
    import { cn } from '$lib/utils/shadcn';

    type CollapseAt = 'sm' | 'md' | 'lg' | 'xl' | '2xl' | 'never';

    interface Props {
        /** Lucide icon component rendered before the label. */
        icon?: Component<IconProps>;
        /**
         * Visual style of the button. One of:
         * `default` | `destructive` | `outline` | `secondary` | `ghost` | `link`.
         */
        variant?: ButtonVariant;
        /**
         * Props forwarded to the underlying shadcn button element
         * (e.g. `onclick`, `disabled`, `title`, `type`, `class`).
         */
        buttonProps?: ButtonProps;
        /**
         * Hide the label at and below the given Tailwind breakpoint while
         * keeping the icon visible. `never` (default) keeps the label at all sizes.
         */
        collapseAt?: CollapseAt;
        /**
         * When true, disables the button and shows an indeterminate linear
         * progress bar at the bottom.
         */
        isPending?: boolean;
        /** Button label content. Omit for an icon-only button. */
        children?: Snippet;
    }

    let {
        icon: Icon,
        variant,
        buttonProps = {},
        collapseAt = 'never',
        isPending = false,
        children
    }: Props = $props();
    const className = $derived(buttonProps.class);
    const disabled = $derived(buttonProps.disabled);
    const restButtonProps = $derived.by(() => {
        const rest = { ...buttonProps };
        delete rest.class;
        delete rest.disabled;
        return rest;
    });

    const labelCollapseClass: Record<CollapseAt, string> = {
        sm: 'max-sm:hidden',
        md: 'max-md:hidden',
        lg: 'max-lg:hidden',
        xl: 'max-xl:hidden',
        '2xl': 'max-2xl:hidden',
        never: ''
    };
</script>

<UiButton
    {variant}
    class={cn('relative', isPending && 'overflow-hidden', className)}
    disabled={isPending || disabled}
    {...restButtonProps}
>
    {#if Icon}
        <Icon class="size-4" />
    {/if}
    {#if children}
        <span class={labelCollapseClass[collapseAt]}>{@render children()}</span>
    {/if}
    {#if isPending}
        <span
            data-testid="button-progress"
            role="progressbar"
            aria-label="Loading"
            class="bg-current/20 pointer-events-none absolute inset-x-0 bottom-0 h-0.5 overflow-hidden"
        >
            <span class="button-progress-indicator absolute inset-y-0 bg-current"></span>
        </span>
    {/if}
</UiButton>

<style>
    .button-progress-indicator {
        animation: button-progress-slide 1.2s ease-in-out infinite;
    }
    @keyframes button-progress-slide {
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
