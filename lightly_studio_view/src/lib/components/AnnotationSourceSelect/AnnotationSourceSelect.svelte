<script lang="ts">
    import * as Select from '$lib/components/ui/select';

    interface Props {
        /** Names of the annotation sources (collections) to choose from. */
        sourceNames: string[];
        /** Currently selected source name. */
        selectedSource?: string;
        /** Optional notification when the selection changes (the value also flows out via `bind:selectedSource`). */
        onSelect?: (source: string) => void;
    }

    let { sourceNames, selectedSource = $bindable(), onSelect }: Props = $props();
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
        {selectedSource ?? 'Select a source...'}
    </Select.Trigger>
    <Select.Content>
        {#each sourceNames as name (name)}
            <Select.Item
                value={name}
                label={name}
                data-testid={`annotation-source-option-${name}`}
            />
        {/each}
    </Select.Content>
</Select.Root>
