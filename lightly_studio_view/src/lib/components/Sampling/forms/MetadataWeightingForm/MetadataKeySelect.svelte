<script lang="ts">
    import * as Select from '$lib/components/ui/select';
    interface Props {
        value: string;
        fieldNames: string[];
        onValueChange: (value: string) => void;
    }
    let { value, fieldNames, onValueChange }: Props = $props();
</script>

<Select.Root type="single" name="metadata-weighting-key" {value} {onValueChange}>
    <Select.Trigger class="w-full" data-testid="strategy-metadata-key-input">
        {value || 'Select a metadata field'}
    </Select.Trigger>
    <Select.Content>
        <Select.Group>
            {#each fieldNames as fieldName (fieldName)}
                <Select.Item value={fieldName} label={fieldName}>
                    {fieldName}
                </Select.Item>
            {/each}
        </Select.Group>
    </Select.Content>
</Select.Root>
