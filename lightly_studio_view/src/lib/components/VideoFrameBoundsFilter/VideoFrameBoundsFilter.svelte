<script lang="ts">
    import { page } from '$app/state';
    import { formatInteger } from '$lib/utils';
    import RangeFilterField from '$lib/components/RangeFilterField/RangeFilterField.svelte';
    import { useVideoFramesBounds } from '$lib/hooks/useVideoFramesBounds/useVideoFramesBounds';

    interface Props {
        /** Called when the frame number filter range changes. */
        onFilterChanged?: (fieldName: string, min: number, max: number) => void;
    }

    const { onFilterChanged }: Props = $props();

    const { videoFramesBounds, videoFramesBoundsValues, updateVideoFramesBoundsValues } =
        useVideoFramesBounds(page.params.collection_id);

    const handleChangeFrameNumber = (newValues: number[]) => {
        if (!$videoFramesBoundsValues) return;
        updateVideoFramesBoundsValues({
            ...$videoFramesBoundsValues,
            frame_number: {
                min: newValues[0],
                max: newValues[1]
            }
        });
        onFilterChanged?.('frame_number', newValues[0], newValues[1]);
    };
</script>

{#if $videoFramesBounds && $videoFramesBoundsValues}
    <RangeFilterField
        label="Frame number"
        minText={formatInteger($videoFramesBoundsValues.frame_number.min)}
        maxText={formatInteger($videoFramesBoundsValues.frame_number.max)}
        min={$videoFramesBounds.frame_number.min}
        max={$videoFramesBounds.frame_number.max}
        value={[
            $videoFramesBoundsValues.frame_number.min,
            $videoFramesBoundsValues.frame_number.max
        ]}
        onValueCommit={handleChangeFrameNumber}
        sliderClass="filter-width"
    />
{/if}
