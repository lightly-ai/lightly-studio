<script lang="ts">
    import { Palette } from '@lucide/svelte';
    import * as Select from '$lib/components/ui/select';
    import { useMetadataFilters } from '$lib/hooks/useMetadataFilters/useMetadataFilters';

    interface Props {
        collectionId: string;
        selectedKey: string | null;
        onSelectedKeyChange: (key: string | null) => void;
    }

    const supportedTypes = new Set(['string', 'boolean']);

    let { collectionId, selectedKey, onSelectedKeyChange }: Props = $props();

    const { metadataInfo } = useMetadataFilters(collectionId);

    const colorableFields = $derived(
        ($metadataInfo ?? []).filter((field) => supportedTypes.has(field.type))
    );

    const isSelectDisabled = $derived(colorableFields.length === 0 && !selectedKey);
    const selectValue = $derived(selectedKey ?? '');
    const triggerLabel = $derived.by(() => {
        if (isSelectDisabled) {
            return 'Nothing to color by';
        }
        return selectedKey ? `metadata.${selectedKey}` : 'Color by';
    });

    const handleValueChange = (value: string) => {
        onSelectedKeyChange(value === '' ? null : value);
    };
</script>

<Select.Root type="single" value={selectValue} allowDeselect onValueChange={handleValueChange}>
    <Select.Trigger
        class="h-8 w-48 gap-2 px-2.5"
        data-testid="plot-color-by-button"
        disabled={isSelectDisabled}
    >
        <div class="flex min-w-0 items-center gap-2">
            <Palette class="h-4 w-4 shrink-0" />
            <span class="truncate">{triggerLabel}</span>
        </div>
    </Select.Trigger>
    <Select.Content class="max-h-64" data-testid="plot-color-by-options">
        {#each colorableFields as field (field.name)}
            <Select.Item value={field.name} label={`metadata.${field.name}`}>
                {`metadata.${field.name}`}
            </Select.Item>
        {/each}
    </Select.Content>
</Select.Root>
