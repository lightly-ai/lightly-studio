<script lang="ts">
    import { Checkbox } from '$lib/components/ui/checkbox';
    import Segment from '$lib/components/Segment/Segment.svelte';
    import {
        MATCH_TYPE_LABELS,
        MATCH_TYPE_ORDER,
        useMatchTypeFilter
    } from '$lib/hooks/useMatchTypeFilter/useMatchTypeFilter';

    const { selectedMatchTypes, toggle } = useMatchTypeFilter();
</script>

<Segment title="Match type">
    <div class="space-y-1.5" data-testid="match-type-filter">
        {#each MATCH_TYPE_ORDER as matchType (matchType)}
            <label
                class="flex cursor-pointer items-center gap-2 rounded-md border border-[#3c3c3c] bg-muted px-2 py-1.5"
            >
                <Checkbox
                    checked={$selectedMatchTypes.has(matchType)}
                    aria-label={MATCH_TYPE_LABELS[matchType]}
                    onCheckedChange={() => toggle(matchType)}
                />
                <span class="text-sm font-medium">{MATCH_TYPE_LABELS[matchType]}</span>
                <span class="ml-auto font-mono text-xs uppercase text-muted-foreground">
                    {matchType}
                </span>
            </label>
        {/each}
    </div>
</Segment>
