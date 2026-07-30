<script lang="ts">
    import { page } from '$app/state';
    import { useVideoBounds } from '$lib/hooks/useVideosBounds/useVideosBounds';
    import { formatInteger } from '$lib/utils';
    import { Slider } from '$lib/components/ui/slider/index.js';

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
    <div class="space-y-1">
        <h2 class="text-md">Width</h2>
        <div class="flex justify-between text-sm text-diffuse-foreground">
            <span>{formatInteger($videoBoundsValues.width.min)}px</span>
            <span>{formatInteger($videoBoundsValues.width.max)}px</span>
        </div>
        <div class="relative p-2">
            <Slider
                type="multiple"
                class="filter-width"
                min={$videoBounds?.width.min}
                max={$videoBounds?.width.max}
                value={[$videoBoundsValues.width.min, $videoBoundsValues.width.max]}
                onValueCommit={handleChangeWidth}
            />
        </div>
    </div>

    <div class="space-y-1">
        <h2 class="text-md">Height</h2>
        <div class="flex justify-between text-sm text-diffuse-foreground">
            <span>{formatInteger($videoBoundsValues.height.min)}px</span>
            <span>{formatInteger($videoBoundsValues.height.max)}px</span>
        </div>
        <div class="relative p-2">
            <Slider
                type="multiple"
                class="filter-height"
                min={$videoBounds.height.min}
                max={$videoBounds.height.max}
                value={[$videoBoundsValues.height.min, $videoBoundsValues.height.max]}
                onValueCommit={handleChangeHeight}
            />
        </div>
    </div>

    {#if $videoBoundsValues.fps.min != $videoBoundsValues.fps.max}
        <div class="space-y-1">
            <h2 class="text-md">FPS</h2>
            <div class="flex justify-between text-sm text-diffuse-foreground">
                <span>{formatInteger($videoBoundsValues.fps.min)}</span>
                <span>{formatInteger($videoBoundsValues.fps.max)}</span>
            </div>
            <div class="relative p-2">
                <Slider
                    type="multiple"
                    class="filter-width"
                    min={$videoBounds?.fps.min}
                    max={$videoBounds?.fps.max}
                    step={0.01}
                    value={[$videoBoundsValues.fps.min, $videoBoundsValues.fps.max]}
                    onValueCommit={handleChangeFps}
                />
            </div>
        </div>
    {/if}

    <div class="space-y-1">
        <h2 class="text-md">Duration</h2>
        <div class="flex justify-between text-sm text-diffuse-foreground">
            <span>{formatInteger($videoBoundsValues.duration_s.min)}s</span>
            <span>{formatInteger($videoBoundsValues.duration_s.max)}s</span>
        </div>
        <div class="relative p-2">
            <Slider
                type="multiple"
                class="filter-width"
                min={$videoBounds.duration_s.min}
                max={$videoBounds.duration_s.max}
                step={0.01}
                value={[$videoBoundsValues.duration_s.min, $videoBoundsValues.duration_s.max]}
                onValueCommit={handleChangeDuration}
            />
        </div>
    </div>
{/if}
