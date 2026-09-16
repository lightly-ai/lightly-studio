<script lang="ts">
    import { page } from '$app/state';
    import { useVideoBounds } from '$lib/hooks/useVideosBounds/useVideosBounds';
    import { formatInteger } from '$lib/utils';
    import RangeFilterField from '$lib/components/RangeFilterField/RangeFilterField.svelte';

    interface Props {
        /** Called when a video field filter (width, height, fps, duration) range changes. */
        onFilterChanged?: (fieldName: string, min: number, max: number) => void;
    }

    const { onFilterChanged }: Props = $props();

    const { videoBounds, videoBoundsValues, updateVideoBoundsValues } = useVideoBounds(
        page.params.collection_id
    );

    const handleChangeWidth = (newValues: number[]) => {
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

    const handleChangeHeight = (newValues: number[]) => {
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

    const handleChangeFps = (newValues: number[]) => {
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

    const handleChangeDuration = (newValues: number[]) => {
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
    <RangeFilterField
        label="Width"
        minText={`${formatInteger($videoBoundsValues.width.min)}px`}
        maxText={`${formatInteger($videoBoundsValues.width.max)}px`}
        min={$videoBounds.width.min}
        max={$videoBounds.width.max}
        value={[$videoBoundsValues.width.min, $videoBoundsValues.width.max]}
        onValueCommit={handleChangeWidth}
        sliderClass="filter-width"
    />

    <RangeFilterField
        label="Height"
        minText={`${formatInteger($videoBoundsValues.height.min)}px`}
        maxText={`${formatInteger($videoBoundsValues.height.max)}px`}
        min={$videoBounds.height.min}
        max={$videoBounds.height.max}
        value={[$videoBoundsValues.height.min, $videoBoundsValues.height.max]}
        onValueCommit={handleChangeHeight}
        sliderClass="filter-height"
    />

    {#if $videoBoundsValues.fps.min != $videoBoundsValues.fps.max}
        <RangeFilterField
            label="FPS"
            minText={formatInteger($videoBoundsValues.fps.min)}
            maxText={formatInteger($videoBoundsValues.fps.max)}
            min={$videoBounds.fps.min}
            max={$videoBounds.fps.max}
            step={0.01}
            value={[$videoBoundsValues.fps.min, $videoBoundsValues.fps.max]}
            onValueCommit={handleChangeFps}
            sliderClass="filter-fps"
        />
    {/if}

    <RangeFilterField
        label="Duration"
        minText={`${formatInteger($videoBoundsValues.duration_s.min)}s`}
        maxText={`${formatInteger($videoBoundsValues.duration_s.max)}s`}
        min={$videoBounds.duration_s.min}
        max={$videoBounds.duration_s.max}
        step={0.01}
        value={[$videoBoundsValues.duration_s.min, $videoBoundsValues.duration_s.max]}
        onValueCommit={handleChangeDuration}
        sliderClass="filter-duration"
    />
{/if}
