<script lang="ts">
    import { Minus, Plus } from '@lucide/svelte';
    import { Button } from '$lib/components';
    import { getNextPointSize } from './pointSize';

    interface Props {
        // Null lets the plot pick the size from the point density.
        pointSize: number | null;
    }

    let { pointSize = $bindable(null) }: Props = $props();

    const buttonClass =
        'size-[26px] text-muted-foreground hover:bg-white/10 hover:text-foreground disabled:opacity-40';
</script>

<div
    class="pointer-events-auto flex shrink-0 items-center gap-0.5 rounded-lg border border-white/10 bg-black/60 p-1 text-xs text-muted-foreground backdrop-blur-sm"
    data-testid="plot-point-size-control"
>
    <Button
        icon={Minus}
        ariaLabel="Smaller points"
        buttonProps={{
            size: 'icon',
            title: 'Smaller points',
            'data-testid': 'plot-point-size-decrease',
            disabled: getNextPointSize(pointSize, -1) === pointSize,
            onclick: () => (pointSize = getNextPointSize(pointSize, -1)),
            class: buttonClass
        }}
    />
    <span
        class="w-8 text-center tabular-nums"
        data-testid="plot-point-size-value"
        title="Point size">{pointSize ?? 'Auto'}</span
    >
    <Button
        icon={Plus}
        ariaLabel="Larger points"
        buttonProps={{
            size: 'icon',
            title: 'Larger points',
            'data-testid': 'plot-point-size-increase',
            disabled: getNextPointSize(pointSize, 1) === pointSize,
            onclick: () => (pointSize = getNextPointSize(pointSize, 1)),
            class: buttonClass
        }}
    />
</div>
