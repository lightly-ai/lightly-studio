<script lang="ts">
    import { page } from '$app/state';
    import { formatInteger } from '$lib/utils';
    import { Slider } from '$lib/components/ui/slider/index.js';
    import type { SliderMultipleRootProps } from 'bits-ui/dist/types';
    import { useVideoFramesBounds } from '$lib/hooks/useVideoFramesBounds/useVideoFramesBounds';
    const { videoFramesBounds, videoFramesBoundsValues, updateVideoFramesBoundsValues } =
        useVideoFramesBounds(page.params.dataset_id);

    const handleChangeFrameNumber: SliderMultipleRootProps['onValueChange'] = (newValues) => {
        if (!$videoFramesBoundsValues) return;
        updateVideoFramesBoundsValues({
            ...$videoFramesBoundsValues,
            frame_number: {
                min: newValues[0],
                max: newValues[1]
            }
        });
    };
</script>

{#if $videoFramesBounds && $videoFramesBoundsValues}
    <div class="space-y-1">
        <h2 class="text-md">Frame number</h2>
        <div class="flex justify-between text-sm text-diffuse-foreground">
            <span>{formatInteger($videoFramesBoundsValues.frame_number.min)}</span>
            <span>{formatInteger($videoFramesBoundsValues.frame_number.max)}</span>
        </div>
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
