<script lang="ts">
    import { Palette } from '@lucide/svelte';
    import * as Select from '$lib/components/ui/select';
    import { useMetadataFilters } from '$lib/hooks/useMetadataFilters/useMetadataFilters';
    import { usePlotColorByType } from './usePlotColorByType/usePlotColorByType';

    interface Props {
        collectionId: string;
        selectedKey: string | null;
        onSelectedKeyChange: (key: string | null) => void;
        withTags: boolean;
    }

    const supportedTypes = new Set(['string', 'boolean']);

    let { collectionId, selectedKey, onSelectedKeyChange, withTags }: Props = $props();

    const { metadataInfo } = useMetadataFilters(collectionId);
    const { selectedColorByType, setSelectedColorByType, clearSelectedColorByType } =
        usePlotColorByType(collectionId);

    const colorableFields = $derived(
        ($metadataInfo ?? []).filter((field) => supportedTypes.has(field.type))
    );

    const colorByOptions = $derived.by(() => {
        const tagsOption = withTags ? [{ value: 'tags', label: 'tags' }] : [];
        const metadataOptions = colorableFields.map((field) => ({
            value: field.name,
            label: `metadata.${field.name}`
        }));

        return [...tagsOption, ...metadataOptions];
    });

    const selectValue = $derived.by(() => {
        if (selectedKey) {
            return selectedKey;
        }
        return $selectedColorByType ?? '';
    });
    const triggerLabel = $derived.by(() => {
        if (selectedKey) {
            return `metadata.${selectedKey}`;
        }
        if ($selectedColorByType === 'annotation_label') {
            return 'annotations';
        }
        if ($selectedColorByType === 'tags') {
            return 'tags';
        }
        return 'Color by';
    });

    const handleValueChange = (value: string) => {
        if (value === '') {
            clearSelectedColorByType();
            onSelectedKeyChange(null);
            return;
        }

        if (value === 'tags') {
            setSelectedColorByType(value);
            onSelectedKeyChange(null);
            return;
        }

        setSelectedColorByType('metadata');
        onSelectedKeyChange(value);
    };
</script>

<Select.Root type="single" value={selectValue} allowDeselect onValueChange={handleValueChange}>
    <Select.Trigger class="h-8 w-48 gap-2 px-2.5" data-testid="plot-color-by-button">
        <div class="flex min-w-0 items-center gap-2">
            <Palette class="h-4 w-4 shrink-0" />
            <span class="truncate">{triggerLabel}</span>
        </div>
    </Select.Trigger>
    <Select.Content class="max-h-64" data-testid="plot-color-by-options">
        {#if colorByOptions.length === 0}
            <p class="px-2 py-1.5 text-sm text-muted-foreground">Nothing to color by</p>
        {/if}
        {#each colorByOptions as option (option.value)}
            <Select.Item value={option.value} label={option.label}>
                {option.label}
            </Select.Item>
        {/each}
    </Select.Content>
</Select.Root>
