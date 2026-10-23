<script lang="ts">
    import { Input } from '$lib/components/ui/input';
    import { Button } from '$lib/components/ui/button';
    import { ArrowRight } from '@lucide/svelte';
    import { cn } from '$lib/utils';
    import { createEmptyTextAxesDraft, toTextAxes } from './textAxesDraft';

    type TextAxesDraft = ReturnType<typeof createEmptyTextAxesDraft>;
    type TextAxes = NonNullable<ReturnType<typeof toTextAxes>>;
    type AnchorKey = keyof TextAxesDraft;

    interface Props {
        // Owned by the parent, so the texts survive when the popover closes.
        draft: TextAxesDraft;
        onCommit: (textAxes: TextAxes) => void;
        onCancel?: () => void;
        // Disables the form while the texts are embedded.
        isPending?: boolean;
    }

    let { draft = $bindable(), onCommit, onCancel, isPending = false }: Props = $props();

    // Set when the user applies with an empty text. Marks the empty inputs.
    let showMissing = $state(false);

    const submit = () => {
        if (isPending) return;
        const textAxes = toTextAxes(draft);
        showMissing = textAxes === null;
        if (textAxes) onCommit(textAxes);
    };
    const onKeyDown = (event: KeyboardEvent) => {
        // During IME composition, Enter confirms the composed text, not the axes.
        if (event.key !== 'Enter' || event.isComposing) return;
        event.preventDefault();
        submit();
    };
</script>

{#snippet anchorInput(key: AnchorKey, label: string, placeholder: string)}
    {@const isMissing = showMissing && !draft[key].trim()}
    <label class="min-w-0 flex-1 space-y-1 text-xs text-muted-foreground">
        <span>{label}</span>
        <Input
            {placeholder}
            aria-label={label}
            aria-invalid={isMissing}
            bind:value={draft[key]}
            disabled={isPending}
            onkeydown={onKeyDown}
            wrapperClass="w-full min-w-0"
            class={cn('h-9 text-sm', isMissing && 'border-destructive')}
            data-testid="plot-text-axis-{key}-input"
        />
    </label>
{/snippet}

<div class="space-y-4">
    <fieldset class="space-y-2">
        <legend class="text-sm font-medium">Horizontal</legend>
        <div class="flex items-end gap-2">
            {@render anchorInput('xNegative', 'Left', 'e.g. night')}
            <ArrowRight class="mb-2.5 h-4 w-4 shrink-0 text-muted-foreground" />
            {@render anchorInput('xPositive', 'Right', 'e.g. day')}
        </div>
    </fieldset>
    <fieldset class="space-y-2">
        <legend class="text-sm font-medium">Vertical</legend>
        <div class="flex items-end gap-2">
            {@render anchorInput('yNegative', 'Bottom', 'e.g. indoors')}
            <ArrowRight class="mb-2.5 h-4 w-4 shrink-0 text-muted-foreground" />
            {@render anchorInput('yPositive', 'Top', 'e.g. outdoors')}
        </div>
    </fieldset>
    {#if showMissing && !toTextAxes(draft)}
        <p role="alert" class="text-sm text-destructive">
            Enter a description for each end of both axes.
        </p>
    {/if}
    <div class="flex justify-end gap-2">
        <Button variant="ghost" size="sm" disabled={isPending} onclick={onCancel}>Cancel</Button>
        <Button size="sm" disabled={isPending} onclick={submit}>
            {isPending ? 'Applying…' : 'Apply axes'}
        </Button>
    </div>
</div>
