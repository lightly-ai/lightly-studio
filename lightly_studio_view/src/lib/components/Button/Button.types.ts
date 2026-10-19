import type { Component, Snippet } from 'svelte';
import type { IconProps } from '@lucide/svelte';
import type { ButtonProps, ButtonVariant } from '$lib/components/ui/button';

type CollapseAt = 'sm' | 'md' | 'lg' | 'xl' | '2xl' | 'never';

/**
 * `ButtonProps` with `disabled` marked deprecated so callers are nudged
 * towards `disabledReason` (tooltip) or `isPending` (loading state).
 */
type ButtonPropsWithDeprecations = Omit<ButtonProps, 'disabled'> & {
    /**
     * @deprecated Prefer `disabledReason` to explain why the button is
     * disabled, or `isPending` for loading states. Use `disabled` only
     * when the button must be silently blocked with no explanation.
     */
    disabled?: boolean | null;
};

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
    buttonProps?: ButtonPropsWithDeprecations;
    /**
     * Hide the label at and below the given Tailwind breakpoint while
     * keeping the icon visible. The label remains in the DOM as visually
     * hidden text so screen readers still announce it. `never` (default)
     * keeps the label visible at all sizes and renders the children
     * unwrapped, so they stay direct flex children of the button.
     */
    collapseAt?: CollapseAt;
    /**
     * When true, disables the button and shows an indeterminate linear
     * progress bar at the bottom.
     */
    isPending?: boolean;
    /**
     * When provided as a non-empty string, the button is automatically
     * disabled and this text is shown in a tooltip on hover explaining why.
     * Callers do not also need to pass `disabled` via `buttonProps`.
     */
    disabledReason?: string;
    onclick?: ButtonProps['onclick'];
}

/**
 * `ariaLabel` is required for icon-only buttons (no `children`) so the
 * button always has an accessible name. When `children` are provided
 * it is optional and overrides the visible label as the accessible name.
 */
export type Props =
    | (BaseProps & { children: Snippet; ariaLabel?: string })
    | (BaseProps & { children?: undefined; ariaLabel: string });
