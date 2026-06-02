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
        icon?: Component<IconProps>;
        variant?: ButtonVariant;
        buttonProps?: ButtonProps;
        collapseAt?: CollapseAt;
        children?: Snippet;
    }

    let { icon: Icon, variant, buttonProps = {}, collapseAt = 'never', children }: Props = $props();
    const { class: className, ...restButtonProps } = buttonProps;

    const labelCollapseClass: Record<CollapseAt, string> = {
        sm: 'max-sm:hidden',
        md: 'max-md:hidden',
        lg: 'max-lg:hidden',
        xl: 'max-xl:hidden',
        '2xl': 'max-2xl:hidden',
        never: ''
    };
</script>

<UiButton {variant} class={cn('flex items-center space-x-2', className)} {...restButtonProps}>
    {#if Icon}
        <Icon class="size-4" />
    {/if}
    {#if children}
        <span class={labelCollapseClass[collapseAt]}>{@render children()}</span>
    {/if}
</UiButton>
