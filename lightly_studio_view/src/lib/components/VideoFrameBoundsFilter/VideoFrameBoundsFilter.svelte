<script lang="ts">
    import { page } from '$app/state';
    import { NumericRangeInputs } from '$lib/components/NumericRangeInputs';
    import { Slider } from '$lib/components/ui/slider/index.js';
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
    <div class="space-y-1">
        <h2 class="text-md">Frame number</h2>
        <NumericRangeInputs
            label="Frame number"
            bound={$videoFramesBounds.frame_number}
            value={$videoFramesBoundsValues.frame_number}
            integer
            onValueCommit={handleChangeFrameNumber}
        />
        <div class="relative p-2">
            <Slider
                type="multiple"
                class="filter-width"
                min={$videoFramesBounds.frame_number.min}
                max={$videoFramesBounds.frame_number.max}
                value={[
                    $videoFramesBoundsValues.frame_number.min,
                    $videoFramesBoundsValues.frame_number.max
                ]}
                onValueCommit={handleChangeFrameNumber}
            />
        </div>
    </div>
{/if}
