<script lang="ts">
    import { Input } from '$lib/components/ui/input';
    import { cn } from '$lib/utils/shadcn';

    interface Props {
        query: string;
        useRegex: boolean;
        invalid: boolean;
        placeholder: string;
        onQueryChange: (query: string) => void;
        onRegexChange: (useRegex: boolean) => void;
    }

    let { query, useRegex, invalid, placeholder, onQueryChange, onRegexChange }: Props = $props();
</script>

<div class="relative">
    <Input
        value={query}
        oninput={(event) => onQueryChange(event.currentTarget.value)}
        {placeholder}
        aria-label={placeholder.replace('…', '')}
        aria-invalid={invalid}
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
        onclick={() => onRegexChange(!useRegex)}>.*</button
    >
</div>
