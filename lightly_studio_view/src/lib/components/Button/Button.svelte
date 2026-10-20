<script lang="ts">
    import type { Component, Snippet } from 'svelte';
    import type { IconProps } from '@lucide/svelte';
    import { Button as UiButton } from '$lib/components/ui/button';
    import type { ButtonProps, ButtonVariant } from '$lib/components/ui/button';
    import { cn } from '$lib/utils/shadcn';
    import { Tooltip } from '$lib/components/ui/tooltip';
    import ButtonProgress from './ButtonProgress.svelte';

    type CollapseAt = 'sm' | 'md' | 'lg' | 'xl' | '2xl' | 'never';

    type ButtonPropsWithDeprecations = Omit<ButtonProps, 'disabled'> & {
        /** @deprecated Prefer `disabledReason` or `isPending`. */
        disabled?: boolean | null;
    };

    interface BaseProps {
        icon?: Component<IconProps>;
        iconAfter?: Component<IconProps>;
        iconAfterClass?: string;
        variant?: ButtonVariant;
        buttonProps?: ButtonPropsWithDeprecations;
        collapseAt?: CollapseAt;
        isPending?: boolean;
        disabledReason?: string;
        onclick?: ButtonProps['onclick'];
    }

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
        disabledReason,
        onclick,
        ariaLabel,
        children
    }: Props = $props();
    const className = $derived(buttonProps.class);
    const disabled = $derived(buttonProps.disabled);
    const restButtonProps = $derived.by(() => {
        const rest = { ...buttonProps };
        delete rest.class;
        delete rest.disabled;
        delete rest.onclick;
        // Anchors ignore the disabled attribute; strip href when disabled by reason
        // so UiButton renders a <button> that properly blocks interaction.
        if (disabledReason && rest.href) {
            delete rest.href;
        }
        return rest;
    });

    // Top-level onclick takes precedence; buttonProps.onclick is the fallback.
    const resolvedOnclick = $derived(onclick ?? buttonProps.onclick);

    const isDisabledByReason = $derived(Boolean(disabledReason));
    const tooltipTriggerClass = $derived.by(() => {
        const classes = typeof className === 'string' ? className.split(/\s+/) : [];
        const layoutClasses = classes.filter((className) =>
            ['w-full', 'flex-1', 'min-w-0', 'shrink-0'].includes(className)
        );
        if (layoutClasses.includes('flex-1')) layoutClasses.push('flex');
        return cn(isDisabledByReason && 'cursor-not-allowed', ...layoutClasses);
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

<Tooltip
    content={disabledReason ?? ''}
    position="top"
    noTriggerRole
    triggerTabIndex={isDisabledByReason ? 0 : undefined}
    triggerClass={tooltipTriggerClass}
    ariaLabel={isDisabledByReason ? ariaLabel : undefined}
>
    <UiButton
        {variant}
        class={cn('relative', isPending && 'overflow-hidden', className)}
        disabled={isPending || Boolean(disabled) || isDisabledByReason}
        aria-label={ariaLabel}
        onclick={resolvedOnclick}
        {...restButtonProps}
    >
        {#if Icon}
            <Icon class="size-4" />
        {/if}
        {#if children}
            {#if collapseAt === 'never'}
                <!-- Rendered unwrapped so the caller's own children stay direct flex
                     children of the button (`justify-between`, `gap-*`, `truncate`). -->
                {@render children()}
            {:else}
                <span class={labelCollapseClass[collapseAt]}>{@render children()}</span>
            {/if}
        {/if}
        {#if IconAfter}
            <IconAfter class={cn('size-4', iconAfterClass)} />
        {/if}
        {#if isPending}
            <ButtonProgress />
        {/if}
    </UiButton>
</Tooltip>
