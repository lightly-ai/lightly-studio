<script lang="ts">
    import type { Component } from 'svelte';
    import type { IconProps } from '@lucide/svelte';
    import Button from './Button.svelte';
    import type { ButtonProps, ButtonVariant } from '$lib/components/ui/button';

    type CollapseAt = 'sm' | 'md' | 'lg' | 'xl' | '2xl' | 'never';

    let {
        label,
        icon,
        iconAfter,
        iconAfterClass,
        variant,
        buttonProps,
        collapseAt,
        isPending,
        disabledReason,
        ariaLabel
    }: {
        label?: string;
        icon?: Component<IconProps>;
        iconAfter?: Component<IconProps>;
        iconAfterClass?: string;
        variant?: ButtonVariant;
        buttonProps?: ButtonProps;
        collapseAt?: CollapseAt;
        isPending?: boolean;
        disabledReason?: string;
        ariaLabel?: string;
    } = $props();
</script>

{#if label !== undefined}
    <Button
        {icon}
        {iconAfter}
        {iconAfterClass}
        {variant}
        {buttonProps}
        {collapseAt}
        {isPending}
        {disabledReason}
        {ariaLabel}
    >
        {label}
    </Button>
{:else}
    <Button
        {icon}
        {iconAfter}
        {iconAfterClass}
        {variant}
        {buttonProps}
        {collapseAt}
        {isPending}
        {disabledReason}
        ariaLabel={ariaLabel ?? 'Icon button'}
    />
{/if}
