<script lang="ts">
    import FilterChip from '$lib/components/FilterChip/FilterChip.svelte';
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { useMetadataFilters } from '$lib/hooks/useMetadataFilters/useMetadataFilters';
    import { formatFloat, formatInteger } from '$lib/utils';

    interface Props {
        collectionId?: string;
    }

    const { collectionId }: Props = $props();

    const { metadataBounds, metadataValues, updateMetadataValues } =
        useMetadataFilters(collectionId);

    type Range = { min: number; max: number };

    // Last narrowed range per key, so the checkbox can re-apply a disabled
    // filter — mirrors how the query filter chip remembers its expression.
    let lastRanges = $state<Record<string, Range>>({});

    const isNarrowed = (key: string): boolean => {
        const bound = $metadataBounds[key];
        const value = $metadataValues[key];
        return !!bound && !!value && (value.min > bound.min || value.max < bound.max);
    };

    // Remember the latest narrowed range of every key.
    $effect(() => {
        for (const key of Object.keys($metadataValues)) {
            if (!isNarrowed(key)) continue;
            const value = $metadataValues[key];
            const last = lastRanges[key];
            if (!last || last.min !== value.min || last.max !== value.max) {
                lastRanges = { ...lastRanges, [key]: { min: value.min, max: value.max } };
            }
        }
    });

    // One chip per key that is narrowed now or has a remembered range: active
    // chips show the current range, disabled ones the remembered range.
    const chips = $derived.by(() => {
        const keys = new Set([
            ...Object.keys(lastRanges),
            ...Object.keys($metadataValues).filter(isNarrowed)
        ]);
        return [...keys]
            .filter((key) => $metadataBounds[key])
            .map((key) => {
                const active = isNarrowed(key);
                const range: Range | undefined = active ? $metadataValues[key] : lastRanges[key];
                return { key, active, range };
            })
            .filter((chip): chip is { key: string; active: boolean; range: Range } => !!chip.range);
    });

    const setRange = (key: string, range: Range) => {
        updateMetadataValues({ ...$metadataValues, [key]: range });
    };

    const handleToggle = (key: string, checked: boolean | 'indeterminate') => {
        const bound = $metadataBounds[key];
        if (!bound) return;
        if (checked && lastRanges[key]) {
            setRange(key, lastRanges[key]);
        } else {
            setRange(key, { min: bound.min, max: bound.max });
        }
    };

    const handleClear = (key: string) => {
        const bound = $metadataBounds[key];
        if (bound) setRange(key, { min: bound.min, max: bound.max });
        lastRanges = Object.fromEntries(
            Object.entries(lastRanges).filter(([rangeKey]) => rangeKey !== key)
        );
    };

    const formatValue = (key: string, value: number): string => {
        const bound = $metadataBounds[key];
        const isInteger = !!bound && Number.isInteger(bound.min) && Number.isInteger(bound.max);
        return isInteger ? formatInteger(value) : formatFloat(value);
    };

    const prettify = (key: string): string => key.replace(/_/g, ' ');
</script>

{#if chips.length > 0}
    <Segment title="Metadata filters">
        <div class="space-y-2">
            {#each chips as chip (chip.key)}
                <FilterChip
                    testId="metadata-filter-chip-{chip.key}"
                    checked={chip.active}
                    title={prettify(chip.key)}
                    checkboxLabel={chip.active
                        ? `Disable ${prettify(chip.key)} filter`
                        : `Enable ${prettify(chip.key)} filter`}
                    onCheckedChange={(checked) => handleToggle(chip.key, checked)}
                    onClear={() => handleClear(chip.key)}
                >
                    {#snippet subtitle()}
                        <div class="truncate text-xs text-muted-foreground">
                            {formatValue(chip.key, chip.range.min)} – {formatValue(
                                chip.key,
                                chip.range.max
                            )}
                        </div>
                    {/snippet}
                </FilterChip>
            {/each}
        </div>
    </Segment>
{/if}
