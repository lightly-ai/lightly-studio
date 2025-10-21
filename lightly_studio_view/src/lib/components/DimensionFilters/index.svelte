<script lang="ts">
    import { formatInteger } from '$lib/utils';
    import { Slider } from '$lib/components/ui/slider/index.js';
    import type { SliderMultipleRootProps } from 'bits-ui/dist/types';
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { useDimensions } from '$lib/hooks/useDimensions/useDimensions';

    const {
        dimensionsBounds: bounds,
        dimensionsValues: values,
        updateDimensionsValues: onChange
    } = useDimensions();

    const handleChangeWidth: SliderMultipleRootProps['onValueChange'] = (newValues) => {
        onChange({
            min_width: newValues[0],
            max_width: newValues[1],
            min_height: $values.min_height,
            max_height: $values.max_height
        });
    };

    const handleChangeHeight: SliderMultipleRootProps['onValueChange'] = (newValues) => {
        onChange({
            min_width: $values.min_width,
            max_width: $values.max_width,
            min_height: newValues[0],
            max_height: newValues[1]
        });
    };
</script>

<Segment title="Metadata">
    <div class="space-y-4">
        <div class="space-y-1">
            <h2 class="text-md">Width Filter</h2>
            <div class="flex justify-between text-sm text-diffuse-foreground">
                <span>{formatInteger($values.min_width)}px</span>
                <span>{formatInteger($values.max_width)}px</span>
            </div>
            <div class="relative p-2">
                <Slider
                    type="multiple"
                    class="filter-width"
                    min={$bounds.min_width}
                    max={$bounds.max_width}
                    value={[$values.min_width, $values.max_width]}
                    onValueChange={handleChangeWidth}
                />
            </div>
        </div>
        <div class="space-y-1">
            <h2 class="text-md">Height Filter</h2>
            <div class="flex justify-between text-sm text-diffuse-foreground">
                <span>{formatInteger($values.min_height)}px</span>
                <span>{formatInteger($values.max_height)}px</span>
            </div>
            <div class="relative p-2">
                <Slider
                    type="multiple"
                    class="filter-height"
                    min={$bounds.min_height}
                    max={$bounds.max_height}
                    value={[$values.min_height, $values.max_height]}
                    onValueChange={handleChangeHeight}
                />
            </div>
        </div>
    </div>
</Segment>
