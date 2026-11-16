<script lang="ts">
    import { page } from '$app/state';
    import { useVideoBounds } from '$lib/hooks';
    import { MetadataFilterItem } from '$lib/components/CombinedMetadataDimensionsFilters/MetadataFilterItem';

    interface Props {
        /** Called when a video field filter (width, height, fps, duration) range changes. */
        onFilterChanged?: (fieldName: string, min: number, max: number) => void;
    }

    const { onFilterChanged }: Props = $props();

    const { videoBounds, videoBoundsValues, updateVideoBoundsValues } = useVideoBounds(
        page.params.collection_id
    );

    const handleChangeWidth = (_key: string, newValues: number[]) => {
        if (!$videoBoundsValues) return;
        updateVideoBoundsValues({
            ...$videoBoundsValues,
            width: {
                min: newValues[0],
                max: newValues[1]
            }
        });
        onFilterChanged?.('width', newValues[0], newValues[1]);
    };

    const handleChangeHeight = (_key: string, newValues: number[]) => {
        if (!$videoBoundsValues) return;
        updateVideoBoundsValues({
            ...$videoBoundsValues,
            height: {
                min: newValues[0],
                max: newValues[1]
            }
        });
        onFilterChanged?.('height', newValues[0], newValues[1]);
    };

    const handleChangeFps = (_key: string, newValues: number[]) => {
        if (!$videoBoundsValues) return;
        updateVideoBoundsValues({
            ...$videoBoundsValues,
            fps: {
                min: newValues[0],
                max: newValues[1]
            }
        });
        onFilterChanged?.('fps', newValues[0], newValues[1]);
    };

    const handleChangeDuration = (_key: string, newValues: number[]) => {
        if (!$videoBoundsValues) return;
        updateVideoBoundsValues({
            ...$videoBoundsValues,
            duration_s: {
                min: newValues[0],
                max: newValues[1]
            }
        });
        onFilterChanged?.('duration_s', newValues[0], newValues[1]);
    };
</script>

{#if $videoBounds && $videoBoundsValues}
    <MetadataFilterItem
        metadataKey="width"
        displayName="Width"
        bound={$videoBounds.width}
        value={$videoBoundsValues.width}
        isInteger={true}
        unit="px"
        onValueCommit={handleChangeWidth}
    />
    <MetadataFilterItem
        metadataKey="height"
        displayName="Height"
        bound={$videoBounds.height}
        value={$videoBoundsValues.height}
        isInteger={true}
        unit="px"
        onValueCommit={handleChangeHeight}
    />
    {#if $videoBounds.fps.min !== $videoBounds.fps.max}
        <MetadataFilterItem
            metadataKey="fps"
            displayName="FPS"
            bound={$videoBounds.fps}
            value={$videoBoundsValues.fps}
            isInteger={false}
            onValueCommit={handleChangeFps}
        />
    {/if}
    <MetadataFilterItem
        metadataKey="duration_s"
        displayName="Duration"
        bound={$videoBounds.duration_s}
        value={$videoBoundsValues.duration_s}
        isInteger={false}
        unit="s"
        onValueCommit={handleChangeDuration}
    />
{/if}
