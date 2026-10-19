<script lang="ts">
    import { ArrowLeftRight, RotateCcw } from '@lucide/svelte';
    import * as Popover from '$lib/components/ui/popover';
    import { Button, buttonVariants } from '$lib/components/ui/button';
    import PlotTextAxesInputs from '../PlotTextAxesInputs/PlotTextAxesInputs.svelte';
    import { createEmptyTextAxesDraft, toTextAxes } from '../PlotTextAxesInputs/textAxesDraft';

    type TextAxes = NonNullable<ReturnType<typeof toTextAxes>>;

    interface Props {
        draft: ReturnType<typeof createEmptyTextAxesDraft>;
        // True while the text layout is shown.
        active: boolean;
        isPending: boolean;
        // Resolves to false when the texts fail to embed. The popover then stays open.
        onCommit: (axes: TextAxes) => Promise<boolean>;
        onReset: () => void;
    }

    let { draft = $bindable(), active, isPending, onCommit, onReset }: Props = $props();
    let open = $state(false);
    let error = $state(false);
    const title = $derived(active ? 'Edit axes' : 'Define axes');

    const changeOpen = (next: boolean) => {
        if (isPending) return;
        error = false;
        open = next;
    };
    const apply = async (axes: TextAxes) => {
        error = false;
        if (await onCommit(axes)) open = false;
        else error = true;
    };
    const reset = () => {
        if (isPending) return;
        onReset();
        changeOpen(false);
    };
</script>

{#snippet resetButton()}
    <Button variant="outline" size="sm" disabled={isPending} onclick={reset}>
        <RotateCcw class="mr-2 h-4 w-4" />
        Reset axes
    </Button>
{/snippet}

<div class="flex flex-wrap items-center gap-2">
    <!-- A function binding, so changeOpen can keep the popover open while the axes apply. -->
    <Popover.Root bind:open={() => open, changeOpen}>
        <Popover.Trigger
            class={buttonVariants({ variant: 'outline', size: 'sm' })}
            disabled={isPending}
        >
            <ArrowLeftRight class="mr-2 h-4 w-4" />
            {title}
        </Popover.Trigger>
        <Popover.Content align="start" class="w-[min(380px,calc(100vw-2rem))] space-y-4">
            <div class="space-y-1">
                <h3 class="text-sm font-semibold">{title}</h3>
                <p class="text-sm text-muted-foreground">
                    Choose descriptions for each end of the axes. Samples will be positioned
                    according to how closely they match.
                </p>
            </div>
            <PlotTextAxesInputs
                bind:draft
                onCommit={apply}
                {isPending}
                onCancel={() => changeOpen(false)}
            />
            {#if error}
                <p role="alert" class="text-sm text-destructive">
                    Could not apply axes. Check your descriptions and try again.
                </p>
            {/if}
            {#if active}
                <div class="space-y-2 border-t pt-4">
                    {@render resetButton()}
                    <p class="text-sm text-muted-foreground">
                        Return to the default plot. Your descriptions will be kept.
                    </p>
                </div>
            {/if}
        </Popover.Content>
    </Popover.Root>
    {#if active}
        {@render resetButton()}
    {/if}
</div>
