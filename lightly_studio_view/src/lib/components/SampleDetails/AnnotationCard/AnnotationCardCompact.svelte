<script lang="ts">
    import { useCustomLabelColors } from '$lib/hooks/useCustomLabelColors';
    import { useSettings } from '$lib/hooks/useSettings';
    import { getColorByLabel, isOverlayTarget, isTextInputTarget } from '$lib/utils';
    import { getShortcutKeys, isDeleteKey, isSearchStartKey } from './annotationCard.helpers';

    interface Props {
        className: string;
        /** Recent classes to offer as one-click relabels, without the current class. */
        recentClasses: string[];
        onPickClass: (className: string) => void;
        /** Opens the class search with the query, empty when the class field is clicked. */
        onSearch: (query: string) => void;
        onRemove: () => void;
        onClose: () => void;
    }

    const { className, recentClasses, onPickClass, onSearch, onRemove, onClose }: Props = $props();
    const { customLabelColorsStore } = useCustomLabelColors();
    const { settingsStore } = useSettings();
    const classColor = (name: string) =>
        $customLabelColorsStore[name]?.color ?? getColorByLabel(name, 1).color;

    // Mounted only in the compact view, so the keys act only there. Capture phase, so Esc
    // closes the card before the panel's own Esc handler switches the tool.
    const handleKeydown = (event: KeyboardEvent) => {
        const inFieldOrMenu = isTextInputTarget(event.target) || isOverlayTarget(event.target);
        if (event.key === 'Escape' && !inFieldOrMenu) {
            event.preventDefault();
            event.stopPropagation();
            onClose();
        } else if (isDeleteKey(event)) {
            event.preventDefault();
            onRemove();
        } else if (isSearchStartKey(event, getShortcutKeys($settingsStore))) {
            event.preventDefault();
            onSearch(event.key);
        }
    };
</script>

<svelte:window onkeydowncapture={handleKeydown} />

<button
    type="button"
    class="flex h-8 w-full items-center rounded-md border bg-background px-2 text-left font-medium hover:border-muted-foreground"
    title="Change class"
    onclick={() => onSearch('')}
>
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
                <span class="size-2 shrink-0 rounded-full" style:background-color={classColor(name)}
                ></span>
                <span class="truncate">{name}</span>
            </button>
        {/each}
    </div>
{/if}
<p class="whitespace-nowrap text-xs text-muted-foreground">
    Type to relabel · Del delete · Esc close
</p>
