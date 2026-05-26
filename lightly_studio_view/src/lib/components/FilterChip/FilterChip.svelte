<script lang="ts">
    import { Checkbox } from '$lib/components/ui/checkbox';
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
        testId
    }: Props = $props();
</script>

<div class="rounded-md border border-amber-500/35 bg-amber-500/10 px-2 py-1.5" data-testid={testId}>
    <div class="flex items-center gap-2">
        <Checkbox {checked} aria-label={checkboxLabel} {onCheckedChange} />
        {#if onclick}
            <button type="button" class="min-w-0 flex-1 cursor-pointer text-left" {onclick}>
                <div class="truncate text-sm font-medium">{title}</div>
                {#if subtitle}{@render subtitle()}{/if}
            </button>
        {:else}
            <div class="min-w-0 flex-1">
                <div class="truncate text-sm font-medium">{title}</div>
                {#if subtitle}{@render subtitle()}{/if}
            </div>
        {/if}
        <button
            class="text-muted-foreground hover:text-foreground"
            onclick={onClear}
            title="Clear {title.toLowerCase()}"
            aria-label="Clear {title.toLowerCase()}"
        >
            <X class="size-4" />
        </button>
    </div>
</div>
