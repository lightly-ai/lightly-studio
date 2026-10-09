<script lang="ts">
    import { Input } from '$lib/components/ui/input';
    import { ArrowLeftRight } from '@lucide/svelte';
    import { cn } from '$lib/utils';
    import { createEmptyTextAxesDraft, toTextAxes } from './textAxesDraft';

    type TextAxesDraft = ReturnType<typeof createEmptyTextAxesDraft>;
    type TextAxes = NonNullable<ReturnType<typeof toTextAxes>>;
    type AnchorKey = keyof TextAxesDraft;

    interface Props {
        // Owned by the parent: the plot unmounts while new embeddings load, and local state
        // would clear the inputs each time.
        draft: TextAxesDraft;
        onCommit: (textAxes: TextAxes) => void;
        // Shows a progress bar on the inputs while the texts are embedded.
        isPending?: boolean;
    }

    let { draft = $bindable(), onCommit, isPending = false }: Props = $props();

    // Set when the user presses Enter with an empty text. Marks the empty inputs.
    let showMissing = $state(false);

    const onKeyDown = (event: KeyboardEvent) => {
        // During IME composition, Enter confirms the composed text, not the axes.
        if (event.key !== 'Enter' || event.isComposing) return;
        event.preventDefault();
        const textAxes = toTextAxes(draft);
        showMissing = textAxes === null;
        if (textAxes === null) return;
        onCommit(textAxes);
        (event.currentTarget as HTMLInputElement | null)?.blur();
    };
</script>

{#snippet anchorInput(key: AnchorKey, label: string, placeholder: string)}
    {@const isMissing = showMissing && !draft[key].trim()}
    <Input
        type="text"
        {placeholder}
        aria-label={label}
        aria-invalid={isMissing}
        bind:value={draft[key]}
        onkeydown={onKeyDown}
        {isPending}
        class={cn('h-8 w-32 text-xs', isMissing && 'border-destructive')}
        data-testid="plot-text-axis-{key}-input"
    />
{/snippet}

<!-- At the top: the legend and the tool pill use the bottom edge of the plot. -->
<div class="pointer-events-none absolute inset-x-0 top-3 z-10 flex justify-center">
    <div class="pointer-events-auto flex items-center gap-2 rounded bg-black/70 px-2 py-1">
        {@render anchorInput('xNegative', 'X axis start', 'X−  (e.g. young)')}
        <ArrowLeftRight class="h-4 w-4 text-white" />
        {@render anchorInput('xPositive', 'X axis end', 'X+  (e.g. old)')}
    </div>
</div>
<!-- The strip is narrow. The rotated bar overflows it in the unrotated layout, but after the
     rotation it stays inside the strip. -->
<div
    class="pointer-events-none absolute inset-y-0 left-0 z-10 flex w-10 items-center justify-center"
>
    <div
        class="pointer-events-auto flex -rotate-90 items-center gap-2 whitespace-nowrap rounded bg-black/70 px-2 py-1"
    >
        {@render anchorInput('yNegative', 'Y axis start', 'Y−  (e.g. sad)')}
        <ArrowLeftRight class="h-4 w-4 text-white" />
        {@render anchorInput('yPositive', 'Y axis end', 'Y+  (e.g. happy)')}
    </div>
</div>
