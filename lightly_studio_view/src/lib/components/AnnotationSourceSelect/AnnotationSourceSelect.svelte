<script lang="ts">
    import { Select } from '$lib/components/Select';

    interface Props {
        /** Names of the annotation sources (collections) to choose from. */
        sourceNames: string[];
        /** Currently selected source name. */
        selectedSource?: string;
        /** Optional notification when the selection changes (the value also flows out via `bind:selectedSource`). */
        onSelect?: (source: string) => void;
    }

    let { sourceNames, selectedSource = $bindable(), onSelect }: Props = $props();

    const items = $derived(
        sourceNames.map((name) => ({
            value: name,
            label: name,
            testId: `annotation-source-option-${name}`
        }))
    );
</script>

<Select
    {items}
    value={selectedSource}
    placeholder="Select a source..."
    class="w-full"
    testId="annotation-source-trigger"
    onValueChange={(value) => {
        selectedSource = value;
        onSelect?.(value);
    }}
/>
