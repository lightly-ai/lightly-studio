<script lang="ts">
    import { Input } from '$lib/components/ui/input';
    import { cn } from '$lib/utils/shadcn';

    interface Props {
        query: string;
        useRegex: boolean;
        invalid: boolean;
        placeholder: string;
    }

    let { query = $bindable(), useRegex = $bindable(), invalid, placeholder }: Props = $props();

    const errorId = $props.id();
</script>

<div>
    <div class="relative">
        <Input
            bind:value={query}
            {placeholder}
            aria-label={placeholder.replace('…', '')}
            aria-invalid={invalid}
            aria-describedby={invalid ? errorId : undefined}
            class={cn('h-8 pr-10', invalid && 'border-destructive focus-visible:ring-destructive')}
        />
        <button
            type="button"
            aria-label="Use regular expression"
            aria-pressed={useRegex}
            title="Use regular expression"
            class={cn(
                'absolute right-1 top-1/2 -translate-y-1/2 rounded px-1.5 py-0.5 font-mono text-xs transition-colors',
                useRegex
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:bg-muted hover:text-foreground'
            )}
            onclick={() => (useRegex = !useRegex)}>.*</button
        >
    </div>
    {#if invalid}
        <p id={errorId} class="mt-1 text-xs text-destructive">Invalid pattern</p>
    {/if}
</div>
