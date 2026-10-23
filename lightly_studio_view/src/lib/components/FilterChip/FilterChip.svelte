<script lang="ts">
    import { Checkbox } from '$lib/components/ui/checkbox';
    import { cn } from '$lib/utils';
    import { X } from '@lucide/svelte';
    import type { Snippet } from 'svelte';

    interface Props {
        checked: boolean;
        title: string;
        checkboxLabel: string;
        onCheckedChange: (checked: boolean | 'indeterminate') => void;
        onClear: () => void;
        onclick?: () => void;
        subtitle?: Snippet;
        /** Replaces the title and subtitle; title still names the clear action. */
        content?: Snippet;
        testId?: string;
    }

    let {
        checked,
        title,
        checkboxLabel,
        onCheckedChange,
        onClear,
        onclick,
        subtitle,
        content,
        testId
    }: Props = $props();
</script>

{#snippet body()}
    {#if content}
        {@render content()}
    {:else}
        <div class="truncate text-sm font-medium" {title}>{title}</div>
        {#if subtitle}{@render subtitle()}{/if}
    {/if}
{/snippet}

<div
    class={cn('rounded-md border border-[#3c3c3c] bg-muted px-2', content ? 'py-2' : 'py-1.5')}
    data-testid={testId}
>
    <div class="flex items-center gap-2">
        <Checkbox {checked} aria-label={checkboxLabel} {onCheckedChange} />
        {#if onclick}
            <button
                type="button"
                class="min-w-0 flex-1 cursor-pointer text-left"
                data-testid={testId ? `${testId}-body` : undefined}
                {onclick}
            >
                {@render body()}
            </button>
        {:else}
            <div class="min-w-0 flex-1">
                {@render body()}
            </div>
        {/if}
        <button
            type="button"
            class="shrink-0 text-muted-foreground hover:text-foreground"
            onclick={onClear}
            title="Clear {title.toLowerCase()}"
            aria-label="Clear {title.toLowerCase()}"
        >
            <X class="size-4" />
        </button>
    </div>
</div>
