<script lang="ts">
    import type { Snippet } from 'svelte';
    import { Typography } from '$lib/components';
    import { cn } from '$lib/utils';

    interface Props {
        title: string;
        class?: string;
        /** Content before the title, such as an icon or a back button. */
        leading?: Snippet;
        /** Content after the title, such as inline controls. */
        children?: Snippet;
        /** Buttons at the right end of the row. */
        actions?: Snippet;
    }

    const { title, class: className, leading, children, actions }: Props = $props();
</script>

<!-- The title has a fixed height of one icon button and stays at the top. Thus it
     is at the same position in each panel, also when the inline content is taller
     or wraps. -->
<div class={cn('flex items-start justify-between gap-2', className)}>
    <div class="flex min-w-0 flex-wrap items-start gap-2">
        <div class="flex h-8 items-center gap-2">
            {@render leading?.()}
            <Typography variant="h5" component="h2" className="text-foreground">
                {title}
            </Typography>
        </div>
        {@render children?.()}
    </div>
    {#if actions}
        <div class="flex min-h-8 shrink-0 items-center gap-1">
            {@render actions()}
        </div>
    {/if}
</div>
