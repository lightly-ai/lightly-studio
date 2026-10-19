<script lang="ts">
    import { Input } from '$lib/components/ui/input';
    import { Button } from '$lib/components/ui/button';
    import { ArrowRight } from '@lucide/svelte';
    import { createEmptyTextAxesDraft, toTextAxes } from './textAxesDraft';

    interface Props {
        draft: ReturnType<typeof createEmptyTextAxesDraft>;
        onCommit: (axes: NonNullable<ReturnType<typeof toTextAxes>>) => void;
        onCancel?: () => void;
        isPending?: boolean;
    }
    let { draft = $bindable(), onCommit, onCancel, isPending = false }: Props = $props();
    let showMissing = $state(false);

    const submit = () => {
        if (isPending) return;
        const axes = toTextAxes(draft);
        showMissing = axes === null;
        if (axes) onCommit(axes);
    };
    const onKeyDown = (event: KeyboardEvent) => {
        if (event.key !== 'Enter' || event.isComposing) return;
        event.preventDefault();
        submit();
    };
</script>

{#snippet input(key: keyof typeof draft, label: string, placeholder: string)}
    <label class="min-w-0 flex-1 space-y-1 text-xs text-muted-foreground">
        <span>{label}</span>
        <Input
            {placeholder}
            aria-label={label}
            aria-invalid={showMissing && !draft[key].trim()}
            bind:value={draft[key]}
            disabled={isPending}
            onkeydown={onKeyDown}
            wrapperClass="w-full min-w-0"
            class="h-9 text-sm"
            data-testid="plot-text-axis-{key}-input"
        />
    </label>
{/snippet}

<div class="space-y-4">
    <fieldset class="space-y-2">
        <legend class="text-sm font-medium">Horizontal</legend>
        <div class="flex items-end gap-2">
            {@render input('xNegative', 'Left', 'e.g. night')}
            <ArrowRight class="mb-2.5 h-4 w-4 shrink-0 text-muted-foreground" />
            {@render input('xPositive', 'Right', 'e.g. day')}
        </div>
    </fieldset>
    <fieldset class="space-y-2">
        <legend class="text-sm font-medium">Vertical</legend>
        <div class="flex items-end gap-2">
            {@render input('yNegative', 'Bottom', 'e.g. indoors')}
            <ArrowRight class="mb-2.5 h-4 w-4 shrink-0 text-muted-foreground" />
            {@render input('yPositive', 'Top', 'e.g. outdoors')}
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
