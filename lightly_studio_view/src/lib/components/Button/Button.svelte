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

    interface BaseProps {
        /** Lucide icon component rendered before the label. */
        icon?: Component<IconProps>;
        /** Lucide icon component rendered after the label. */
        iconAfter?: Component<IconProps>;
        /** Additional class applied to the trailing icon (merged with `size-4`). */
        iconAfterClass?: string;
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
         * keeping the icon visible. The label remains in the DOM as visually
         * hidden text so screen readers still announce it. `never` (default)
         * keeps the label visible at all sizes.
         */
        collapseAt?: CollapseAt;
        /**
         * When true, disables the button and shows an indeterminate linear
         * progress bar at the bottom.
         */
        isPending?: boolean;
    }

    /**
     * `ariaLabel` is required for icon-only buttons (no `children`) so the
     * button always has an accessible name. When `children` are provided
     * it is optional and overrides the visible label as the accessible name.
     */
    type Props =
        | (BaseProps & { children: Snippet; ariaLabel?: string })
        | (BaseProps & { children?: undefined; ariaLabel: string });

    let {
        icon: Icon,
        iconAfter: IconAfter,
        iconAfterClass,
        variant = 'ghost',
        buttonProps = {},
        collapseAt = 'never',
        isPending = false,
        ariaLabel,
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
        sm: 'max-sm:sr-only',
        md: 'max-md:sr-only',
        lg: 'max-lg:sr-only',
        xl: 'max-xl:sr-only',
        '2xl': 'max-2xl:sr-only',
        never: ''
    };
</script>

<UiButton
    {variant}
    class={cn('relative', isPending && 'overflow-hidden', className)}
    disabled={isPending || disabled}
    aria-label={ariaLabel}
    {...restButtonProps}
>
    {#if Icon}
        <Icon class="size-4" />
    {/if}
    {#if children}
        <span class={labelCollapseClass[collapseAt]}>{@render children()}</span>
    {/if}
    {#if IconAfter}
        <IconAfter class={cn('size-4', iconAfterClass)} />
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
