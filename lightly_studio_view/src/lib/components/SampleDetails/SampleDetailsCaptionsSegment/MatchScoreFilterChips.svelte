<script lang="ts">
    import { Button } from '$lib/components/ui/button';
    import type { MatchScoreFilter } from '$lib/utils';

    interface MatchScoreFilterChipsProps {
        value: MatchScoreFilter;
        onChange: (filter: MatchScoreFilter) => void;
    }

    const { value, onChange }: MatchScoreFilterChipsProps = $props();

    const filters: { id: MatchScoreFilter; label: string }[] = [
        { id: 'all', label: 'All' },
        { id: 'low', label: 'Low' },
        { id: 'medium', label: 'Med' },
        { id: 'high', label: 'High' }
    ];
</script>

<div
    class="flex flex-wrap items-center gap-1.5"
    role="group"
    aria-label="Filter captions by match score"
    data-testid="match-score-filter-chips"
>
    <span class="mr-1 text-xs text-muted-foreground">Match</span>
    {#each filters as filter (filter.id)}
        <Button
            type="button"
            size="sm"
            variant={value === filter.id ? 'default' : 'outline'}
            class="h-7 px-2.5 text-xs"
            onclick={() => onChange(filter.id)}
            data-testid={`match-score-filter-${filter.id}`}
            aria-pressed={value === filter.id}
        >
            {filter.label}
        </Button>
    {/each}
</div>
