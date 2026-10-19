<script lang="ts">
    import { toTextAxes } from '../PlotTextAxesInputs/textAxesDraft';

    interface Props {
        axes: NonNullable<ReturnType<typeof toTextAxes>>;
    }
    let { axes }: Props = $props();
</script>

<!-- Only the labels take the pointer, so a hover shows the full text and the plot stays usable. -->
{#snippet label(text: string, position: string)}
    <span
        class="pointer-events-auto absolute max-w-[35%] truncate rounded bg-background/90 px-2 py-1 text-xs text-foreground shadow-sm {position}"
        title={text}
    >
        {text}
    </span>
{/snippet}

<div class="pointer-events-none absolute inset-0" aria-label="Applied axis descriptions">
    {@render label(axes.x.negative, 'left-2 top-1/2 -translate-y-1/2')}
    {@render label(axes.x.positive, 'right-2 top-1/2 -translate-y-1/2')}
    {@render label(axes.y.positive, 'left-1/2 top-2 -translate-x-1/2')}
    {@render label(axes.y.negative, 'bottom-12 left-1/2 -translate-x-1/2')}
</div>
