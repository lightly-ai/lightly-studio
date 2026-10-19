<script lang="ts">
    import { Button as UiButton } from '$lib/components/ui/button';
    import { cn } from '$lib/utils/shadcn';
    import { Tooltip } from '$lib/components/ui/tooltip';
    import ButtonProgress from './ButtonProgress.svelte';
    import type { Props } from './Button.types';

    type CollapseAt = NonNullable<Props['collapseAt']>;

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
        return rest;
    });

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
>
    <UiButton
        {variant}
        class={cn(
            'relative',
            isPending && 'overflow-hidden',
            isDisabledByReason && 'disabled:opacity-100',
            className
        )}
        disabled={isPending || Boolean(disabled) || isDisabledByReason}
        aria-label={ariaLabel}
        {onclick}
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

