<script lang="ts">
    import * as Select from '$lib/components/ui/select';

    type SourceOption = {
        id: string;
        name: string;
    };

    interface Props {
        /** Annotation sources (collections) to choose from. */
        sourceOptions?: SourceOption[];
        /** Backward-compatible list of source names where the value is also the display label. */
        sourceNames?: string[];
        /** Currently selected source name. */
        selectedSource?: string;
        /** Optional notification when the selection changes (the value also flows out via `bind:selectedSource`). */
        onSelect?: (source: string) => void;
    }

    let { sourceOptions, sourceNames, selectedSource = $bindable(), onSelect }: Props = $props();

    const options = $derived(
        sourceOptions ??
            sourceNames?.map((name) => ({
                id: name,
                name
            })) ??
            []
    );
</script>

<Select.Root
    type="single"
    value={selectedSource}
    onValueChange={(value) => {
        selectedSource = value;
        onSelect?.(value);
    }}
>
    <Select.Trigger class="w-full" data-testid="annotation-source-trigger">
        {options.find((source) => source.id === selectedSource)?.name ?? 'Select a source...'}
    </Select.Trigger>
    <Select.Content>
        {#each options as source (source.id)}
            <Select.Item
                value={source.id}
                label={source.name}
                data-testid={`annotation-source-option-${source.name}`}
            />
        {/each}
    </Select.Content>
</Select.Root>
