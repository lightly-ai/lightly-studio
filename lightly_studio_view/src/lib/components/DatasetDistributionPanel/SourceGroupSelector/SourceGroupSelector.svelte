<script lang="ts">
    import { Select, type SelectItem } from '$lib/components/Select';

    interface Props {
        sourceItems: SelectItem[];
        groupItems: SelectItem[];
        activeSourceId: string;
        activeGroupId: string | undefined;
        groupLabel: string;
        onSourceChange: (id: string) => void;
        onGroupChange: (id: string) => void;
    }

    const {
        sourceItems,
        groupItems,
        activeSourceId,
        activeGroupId,
        groupLabel,
        onSourceChange,
        onGroupChange
    }: Props = $props();
</script>

<!-- Fixed-width labels + flex-1 triggers keep both selects the same
     width, filling the panel row. -->
<div class="mt-2 flex flex-col gap-2" data-testid="dataset-distribution-source">
    <div class="flex items-center gap-2">
        <span class="w-[100px] shrink-0 text-xs text-muted-foreground">Distribution</span>
        <Select
            items={sourceItems}
            value={activeSourceId}
            size="xs"
            class="min-w-0 flex-1"
            testId="dataset-distribution-source-select"
            onValueChange={onSourceChange}
        />
    </div>

    {#if groupItems.length > 0}
        <div class="flex items-center gap-2">
            <span class="w-[100px] shrink-0 text-xs text-muted-foreground">{groupLabel}</span>
            <Select
                items={groupItems}
                value={activeGroupId}
                size="xs"
                class="min-w-0 flex-1"
                testId="dataset-distribution-group-select"
                onValueChange={onGroupChange}
            />
        </div>
    {/if}
</div>
