<script lang="ts">
    import { cn } from '$lib/utils';
    import { Check, Minus } from '@lucide/svelte';

    interface Props {
        label: string;
        included: boolean;
        excluded: boolean;
        onclick: () => void;
    }
    const { label, included, excluded, onclick }: Props = $props();
    const descriptionId = $props.id();
    const state = $derived(excluded ? 'excluded' : included ? 'included' : 'neutral');
    const description = $derived(
        excluded
            ? 'Excluded. Activate to clear this filter.'
            : included
              ? 'Included. Activate to exclude this tag.'
              : 'Not filtered. Activate to include this tag.'
    );
</script>

<button
    type="button"
    role="checkbox"
    aria-label={label}
    aria-checked={excluded ? 'mixed' : included}
    aria-describedby={descriptionId}
    data-state={state}
    title={description}
    class="group flex w-full min-w-0 items-center gap-2 rounded-sm text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
    {onclick}
>
    <span
        aria-hidden="true"
        class={cn(
            'box-content flex size-4 shrink-0 items-center justify-center rounded-sm border',
            excluded
                ? 'border-red-500 bg-red-500/10 text-red-400'
                : included
                  ? 'border-primary bg-primary text-primary-foreground'
                  : 'border-primary'
        )}
    >
        {#if excluded}<Minus class="size-3.5" />
        {:else if included}<Check class="size-3.5" />{/if}
    </span>
    <span class="min-w-0 flex-1 truncate text-sm font-medium leading-none" title={label}>
        {label}
    </span>
    <span id={descriptionId} class="sr-only">{description}</span>
</button>
