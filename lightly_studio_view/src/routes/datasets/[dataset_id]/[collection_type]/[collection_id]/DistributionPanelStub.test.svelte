<script lang="ts">
    interface Props {
        sources: { id: string; label: string }[];
        onComparisonTagIdsChange?: (ids: string[]) => void;
        onGroupChange?: (sourceId: string, groupId: string | undefined) => void;
        initialSourceId?: string;
        initialGroupId?: string;
    }

    let {
        sources,
        onComparisonTagIdsChange,
        onGroupChange,
        initialSourceId,
        initialGroupId
    }: Props = $props();
    const selections: [string, string | undefined][] = [
        ['classes', 'all'],
        ['metadata', 'city'],
        ['metadata', 'score'],
        ['metadata', undefined]
    ];
</script>

<button data-testid="distribution-select-tag" onclick={() => onComparisonTagIdsChange?.(['tag-a'])}>
    Select tag
</button>
{#each selections as [sourceId, groupId]}
    <button
        data-testid={`distribution-select-${sourceId}-${groupId}`}
        onclick={() => onGroupChange?.(sourceId, groupId)}
    >
        {sourceId}/{groupId}
    </button>
{/each}

<span data-testid="distribution-initial">{initialSourceId}/{initialGroupId}</span>

{#each sources as source}
    <span>{source.label}</span>
{/each}
