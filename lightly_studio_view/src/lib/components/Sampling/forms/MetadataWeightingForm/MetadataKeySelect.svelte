<script lang="ts">
    import { Select } from '$lib/components/Select';

    interface Props {
        value: string;
        fieldNames: string[];
        onValueChange: (value: string) => void;
        testId?: string;
    }
    let {
        value,
        fieldNames,
        onValueChange,
        testId = 'strategy-metadata-key-input'
    }: Props = $props();

    const items = $derived(fieldNames.map((name) => ({ value: name, label: name })));
</script>

<Select
    {items}
    {value}
    {onValueChange}
    placeholder="Select a metadata field"
    class="w-full"
    {testId}
/>
