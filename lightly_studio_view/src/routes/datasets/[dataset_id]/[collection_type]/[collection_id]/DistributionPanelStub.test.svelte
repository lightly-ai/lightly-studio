<script lang="ts">
    interface Props {
        onComparisonTagIdsChange?: (ids: string[]) => void;
        onGroupChange?: (sourceId: string, groupId: string | undefined) => void;
    }

    let { onComparisonTagIdsChange, onGroupChange }: Props = $props();
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
