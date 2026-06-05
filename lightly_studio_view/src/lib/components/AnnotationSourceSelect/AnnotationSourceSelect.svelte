<script lang="ts">
    import { Select } from '$lib/components/Select';

    interface SourceOption {
        id: string;
        name: string;
    }

    interface Props {
        /** Annotation sources (collections) to choose from. */
        sourceOptions: SourceOption[];
        /** Currently selected source id. */
        selectedSource?: string;
        /** Optional notification when the selection changes (the value also flows out via `bind:selectedSource`). */
        onSelect?: (sourceId: string) => void;
        /** `id` forwarded to the trigger element so a `<label for>` can reference it. */
        id?: string;
    }

    let { sourceOptions, selectedSource = $bindable(), onSelect, id }: Props = $props();

    const items = $derived(
        sourceOptions.map((option) => ({
            value: option.id,
            label: option.name,
            testId: `annotation-source-option-${option.name}`
        }))
    );
</script>

<Select
    {items}
    value={selectedSource}
    placeholder="Select a source..."
    class="w-full"
    testId="annotation-source-trigger"
    selectProps={id ? { id } : undefined}
    onValueChange={(value) => {
        selectedSource = value;
        onSelect?.(value);
    }}
/>
