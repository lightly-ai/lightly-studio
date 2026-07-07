<script lang="ts">
    import { Palette } from '@lucide/svelte';
    import { Select, SelectMenuItem } from '$lib/components/Select';
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

    // Sentinel value for the explicit "no coloring" option. Kept distinct from
    // both the numeric option indices and the empty-string deselect signal.
    const NO_COLOR_BY = 'no_color_by';

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
        return idx >= 0 ? String(idx) : NO_COLOR_BY;
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
        if (value === '' || value === NO_COLOR_BY) {
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

<Select
    icon={Palette}
    {triggerLabel}
    value={selectValue}
    allowDeselect
    onValueChange={handleValueChange}
    size="xs"
    class="w-48"
    testId="plot-color-by-button"
>
    {#snippet children()}
        {#if colorByOptions.length === 0}
            <p class="px-2 py-1.5 text-sm text-muted-foreground">Nothing to color by</p>
        {:else}
            <SelectMenuItem value={NO_COLOR_BY} label="No coloring">No coloring</SelectMenuItem>
            {#each colorByOptions as option, i (option.type === 'metadata' ? `metadata:${option.fieldName}` : `type:${option.type}`)}
                <SelectMenuItem value={String(i)} label={option.label}>
                    {option.label}
                </SelectMenuItem>
            {/each}
        {/if}
    {/snippet}
</Select>
