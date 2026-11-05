<script lang="ts">
    import { Kbd } from '$lib/components/ui/kbd';
    import { isDeleteKey, isOverlayTarget, isRelabelKey, isTextInputTarget } from '$lib/utils';
    import { ColorDot } from '../ColorDot';

    interface Props {
        className: string;
        /** Whether to mark the class with its color, as the canvas does when coloring by class. */
        showClassColor: boolean;
        /** Whether the card is shown. A hidden card's keys must not act on the selection. */
        isActive: boolean;
        /** Recent classes to offer as one-click relabels, without the current class. */
        recentClasses: string[];
        onPickClass: (className: string) => void;
        /** Opens the class search. */
        onSearch: () => void;
        onRemove: () => void;
        onClose: () => void;
    }

    const {
        className,
        showClassColor,
        isActive,
        recentClasses,
        onPickClass,
        onSearch,
        onRemove,
        onClose
    }: Props = $props();

    // Mounted only in the compact view, so the keys act only there. Capture phase, so Esc
    // closes the card before the panel's own Esc handler switches the tool.
    const handleKeydown = (event: KeyboardEvent) => {
        if (!isActive) return;
        const inFieldOrMenu = isTextInputTarget(event.target) || isOverlayTarget(event.target);
        if (event.key === 'Escape' && !inFieldOrMenu) {
            event.preventDefault();
            event.stopPropagation();
            onClose();
        } else if (isDeleteKey(event)) {
            event.preventDefault();
            onRemove();
        } else if (isRelabelKey(event)) {
            event.preventDefault();
            onSearch();
        }
    };
</script>

<svelte:window onkeydowncapture={handleKeydown} />

<button
    type="button"
    class="flex h-8 w-full items-center gap-1.5 rounded-md border bg-background px-2 text-left font-medium hover:border-muted-foreground"
    title="Change class"
    aria-label="Change class, current {className}"
    onclick={onSearch}
>
    {#if showClassColor}
        <ColorDot label={className} testId="annotation-card-class-dot" />
    {/if}
    <span class="truncate">{className}</span>
</button>
{#if recentClasses.length > 0}
    <div class="flex flex-wrap items-center gap-1">
        <span class="text-xs text-muted-foreground">Recent</span>
        {#each recentClasses as name (name)}
            <button
                type="button"
                class="inline-flex max-w-full items-center gap-1 rounded-full border px-2 py-0.5 text-xs hover:bg-accent"
                data-testid="annotation-card-recent-class"
                onclick={() => onPickClass(name)}
            >
                <ColorDot label={name} />
                <span class="truncate">{name}</span>
            </button>
        {/each}
    </div>
{/if}
<p
    class="flex items-center gap-1 whitespace-nowrap text-xs text-muted-foreground"
    data-testid="annotation-card-hints"
>
    <Kbd>Enter</Kbd> relabel · <Kbd>Del</Kbd> delete · <Kbd>Esc</Kbd> close
</p>
