<script lang="ts">
    import type { Snippet } from 'svelte';
    import X from '@lucide/svelte/icons/x';
    import { Button } from '$lib/components';
    import { cn } from '$lib/utils';

    /**
     * One panel of the 3D workspace: a header with the title, actions and a close button.
     * A panel hides completely through `onHide`; the layout toggles bring it back.
     */
    interface Props {
        title: string;
        /** Shows the close button. */
        onHide?: () => void;
        /** Controls left of the close button, such as settings. */
        actions?: Snippet;
        children?: Snippet;
        class?: string;
        /** Extra classes of the header, such as a sticky position inside a scroller. */
        headerClass?: string;
        testId?: string;
    }

    let {
        title,
        onHide,
        actions,
        children,
        class: className,
        headerClass,
        testId
    }: Props = $props();

    const panelName = $derived(title.toLowerCase());
</script>

<section
    class={cn('flex min-h-0 flex-col bg-background', className)}
    aria-label={title}
    data-testid={testId}
>
    <header
        class={cn(
            'flex h-8 shrink-0 items-center justify-between gap-2 bg-background px-3 text-xs',
            headerClass
        )}
    >
        <span class="truncate text-muted-foreground">{title}</span>
        <div class="flex items-center gap-1">
            {@render actions?.()}
            {#if onHide}
                <Button
                    variant="ghost"
                    icon={X}
                    ariaLabel={`Hide ${panelName}`}
                    buttonProps={{
                        type: 'button',
                        size: 'xs',
                        class: 'h-7 w-7 p-0',
                        title: `Hide ${panelName}`,
                        onclick: onHide
                    }}
                />
            {/if}
        </div>
    </header>
    <div class="min-h-0 flex-1">{@render children?.()}</div>
</section>
