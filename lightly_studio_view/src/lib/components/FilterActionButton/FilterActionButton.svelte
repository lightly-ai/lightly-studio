<script lang="ts">
    import type { Component } from 'svelte';
    import type { IconProps } from '@lucide/svelte';
    import { Button } from '$lib/components';

    interface Props {
        label: string;
        icon: Component<IconProps>;
        onclick: () => void;
    }

    let { label, icon, onclick }: Props = $props();
</script>

<Button
    {icon}
    variant="outline"
    {onclick}
    buttonProps={{
        size: 'xs',
        class: 'h-6 shrink-0 gap-1 border-border bg-muted/40 px-2 text-foreground/80 hover:bg-muted hover:text-foreground'
    }}
>
    {label}
</Button>
