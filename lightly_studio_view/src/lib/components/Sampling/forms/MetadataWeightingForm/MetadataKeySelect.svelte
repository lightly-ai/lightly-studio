<script lang="ts">
    import { Select } from '$lib/components/Select';

    interface Props {
        value: string;
        fieldNames: string[];
        onValueChange: (value: string) => void;
    }
    let { value, fieldNames, onValueChange }: Props = $props();

    const items = $derived(fieldNames.map((name) => ({ value: name, label: name })));
</script>

<Select
    {items}
    {value}
    {onValueChange}
    placeholder="Select a metadata field"
    class="w-full"
    testId="strategy-metadata-key-input"
/>
