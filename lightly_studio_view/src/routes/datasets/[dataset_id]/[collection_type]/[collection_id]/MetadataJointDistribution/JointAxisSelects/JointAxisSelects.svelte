<script lang="ts">
    import { Select } from '$lib/components/Select';

    interface Props {
        /** The metadata keys that can be an axis. */
        keys: string[];
        xKey: string;
        yKey: string;
        binCount: number;
        onXKeyChange: (key: string) => void;
        onYKeyChange: (key: string) => void;
        onBinCountChange: (binCount: number) => void;
    }

    const { keys, xKey, yKey, binCount, onXKeyChange, onYKeyChange, onBinCountChange }: Props =
        $props();

    // The server accepts at most 50 buckets per numeric axis.
    const BIN_COUNT_ITEMS = [5, 10, 20, 50].map((count) => ({
        value: String(count),
        label: String(count)
    }));
    const keyItems = $derived(keys.map((key) => ({ value: key, label: key })));
</script>

<!-- Fixed-width labels + flex-1 triggers match the rows of the distribution panel. -->
<div class="mt-2 flex flex-col gap-2">
    <div class="flex items-center gap-2">
        <span class="w-[100px] shrink-0 text-xs text-muted-foreground">X axis</span>
        <Select
            items={keyItems}
            value={xKey}
            size="xs"
            class="min-w-0 flex-1"
            testId="joint-distribution-x-key-select"
            onValueChange={onXKeyChange}
        />
    </div>
    <div class="flex items-center gap-2">
        <span class="w-[100px] shrink-0 text-xs text-muted-foreground">Y axis</span>
        <Select
            items={keyItems}
            value={yKey}
            size="xs"
            class="min-w-0 flex-1"
            testId="joint-distribution-y-key-select"
            onValueChange={onYKeyChange}
        />
    </div>
    <div class="flex items-center gap-2">
        <span class="w-[100px] shrink-0 text-xs text-muted-foreground">Numeric bins</span>
        <Select
            items={BIN_COUNT_ITEMS}
            value={String(binCount)}
            size="xs"
            class="min-w-0 flex-1"
            testId="joint-distribution-bin-count-select"
            onValueChange={(value) => onBinCountChange(Number(value))}
        />
    </div>
</div>
