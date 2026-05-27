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
        withAnnotationLabels: boolean;
    }

    const supportedTypes = new Set(['string', 'boolean']);

    let { collectionId, selectedKey, onSelectedKeyChange, withTags, withAnnotationLabels }: Props =
        $props();

    const { metadataInfo } = useMetadataFilters(collectionId);
    const { selectedColorByType, setSelectedColorByType, clearSelectedColorByType } =
        usePlotColorByType(collectionId);

    const colorableFields = $derived(
        ($metadataInfo ?? []).filter((field) => supportedTypes.has(field.type))
    );

    type ColorByOption =
        | { type: 'tags'; label: string }
        | { type: 'annotation_label'; label: string }
        | { type: 'metadata'; label: string; fieldName: string };

    const colorByOptions = $derived.by((): ColorByOption[] => {
        const tagsOption: ColorByOption[] = withTags ? [{ type: 'tags', label: 'tags' }] : [];
        const annotationLabelsOption: ColorByOption[] = withAnnotationLabels
            ? [{ type: 'annotation_label', label: 'annotations' }]
            : [];
        const metadataOptions: ColorByOption[] = colorableFields.map((field) => ({
            type: 'metadata',
            label: `metadata.${field.name}`,
            fieldName: field.name
        }));

        return [...tagsOption, ...annotationLabelsOption, ...metadataOptions];
    });

    const selectValue = $derived.by(() => {
        const idx = colorByOptions.findIndex((opt) => {
            if (opt.type === 'metadata') {
                return opt.fieldName === selectedKey;
            }
            return !selectedKey && opt.type === $selectedColorByType;
        });
        return idx >= 0 ? String(idx) : '';
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

        const option = colorByOptions[Number(value)];
        if (!option) return;

        if (option.type === 'tags') {
            setSelectedColorByType('tags');
            onSelectedKeyChange(null);
        } else if (option.type === 'annotation_label') {
            setSelectedColorByType('annotation_label');
            onSelectedKeyChange(null);
        } else {
            setSelectedColorByType('metadata');
            onSelectedKeyChange(option.fieldName);
        }
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
        {#each colorByOptions as option, i (option.type === 'metadata' ? `metadata:${option.fieldName}` : `type:${option.type}`)}
            <Select.Item value={String(i)} label={option.label}>
                {option.label}
            </Select.Item>
        {/each}
    </Select.Content>
</Select.Root>
