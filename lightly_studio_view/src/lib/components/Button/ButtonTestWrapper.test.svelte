<script lang="ts">
    import type { Component } from 'svelte';
    import type { IconProps } from '@lucide/svelte';
    import Button from './Button.svelte';
    import type { ButtonProps, ButtonVariant } from '$lib/components/ui/button';

    type CollapseAt = 'sm' | 'md' | 'lg' | 'xl' | '2xl' | 'never';

    let {
        label,
        icon,
        variant,
        buttonProps,
        collapseAt,
        isPending
    }: {
        label?: string;
        icon?: Component<IconProps>;
        variant?: ButtonVariant;
        buttonProps?: ButtonProps;
        collapseAt?: CollapseAt;
        isPending?: boolean;
    } = $props();
</script>

{#if label !== undefined}
    <Button {icon} {variant} {buttonProps} {collapseAt} {isPending}>
        {label}
    </Button>
{:else}
    <Button {icon} {variant} {buttonProps} {collapseAt} {isPending} />
{/if}
