<script lang="ts">
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { Checkbox } from '$lib/components/ui/checkbox/index.js';
    import { ColorPicker } from '$lib/components/ui/color-picker';
    import { Label } from '$lib/components/ui/label/index.js';
    import { useCustomLabelColors } from '$lib/hooks/useCustomLabelColors';
    import type { Annotation } from '$lib/types';
    import { formatInteger, getColorByLabel } from '$lib/utils';
    import { type Writable } from 'svelte/store';

    let {
        annotationFilters,
        onToggleAnnotationFilter
    }: {
        annotationFilters: Writable<Annotation[]>;
        onToggleAnnotationFilter: (label: string) => void;
    } = $props();

    const { setCustomColor, getCustomColor, hasCustomColor, customLabelColorsStore } =
        useCustomLabelColors();

    function handleColorChange(label: string, color: string, alpha: number) {
        setCustomColor(label, color, alpha);
    }

    function getInitialColor(label: string) {
        if (hasCustomColor(label)) {
            const customColor = getCustomColor(label);
            return customColor?.color || '#ff0000';
        }

        // Extract a color from the default algorithm
        const defaultColor = getColorByLabel(label, 1).color;
        // Try to convert rgba to hex
        try {
            const rgba = defaultColor.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
            if (rgba) {
                const r = parseInt(rgba[1]);
                const g = parseInt(rgba[2]);
                const b = parseInt(rgba[3]);
                return `#${((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1)}`;
            }
        } catch (e) {
            console.error('Error converting rgba to hex', e);
        }

        return '#ff0000'; // Default fallback
    }

    function getInitialAlpha(label: string) {
        if (hasCustomColor(label)) {
            const customColor = getCustomColor(label);
            return customColor?.alpha || 1.0;
        }
        return 0.4;
    }

    const colorInfos = $derived.by(() => {
        const colors = $customLabelColorsStore;
        const out: Record<string, { borderColor: string; backgroundColor: string }> = {};

        for (const label of Object.keys(colors)) {
            const custom = colors[label];
            out[label] = {
                borderColor: custom.color,
                backgroundColor: getColorByLabel(label, 0.4).color
            };
        }
        return out;
    });
</script>

<Segment title="Labels">
    <div class="width-full space-y-2 overflow-hidden">
        {#each $annotationFilters as { label_name, current_count, total_count, selected } (label_name)}
            <div class="width-full flex items-center space-x-2" title={label_name}>
                <Checkbox
                    id={label_name}
                    checked={selected}
                    aria-labelledby={`${label_name}-label`}
                    onCheckedChange={() => onToggleAnnotationFilter(label_name)}
                />

                <Label
                    id={`${label_name}-label`}
                    for={label_name}
                    data-testid="labels-menu-item"
                    class="flex min-w-0 flex-1 cursor-pointer items-center space-x-2 text-nowrap peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                >
                    <!-- Color picker wrapper with strong event isolation -->
                    <div class="color-picker-container">
                        <ColorPicker
                            initialColor={getInitialColor(label_name)}
                            initialAlpha={getInitialAlpha(label_name)}
                            onChange={(color, alpha) => handleColorChange(label_name, color, alpha)}
                        >
                            <div
                                class="h-3 w-3 cursor-pointer rounded-sm border"
                                style={`
                                    border-color: ${
                                        colorInfos[label_name]?.borderColor ??
                                        getColorByLabel(label_name).color
                                    };
                                    background-color: ${
                                        colorInfos[label_name]?.backgroundColor ??
                                        getColorByLabel(label_name, selected ? 1 : 0.4).color
                                    };
                                `}
                            ></div>
                        </ColorPicker>
                    </div>

                    <p
                        class="flex-1 truncate text-base font-normal"
                        data-testid="label-menu-label-name"
                    >
                        {label_name}
                    </p>
                    {#if current_count}
                        <span
                            class="text-diffuse-foreground text-sm"
                            data-testid="label-menu-label-count"
                            >{formatInteger(current_count)} of {formatInteger(total_count)}</span
                        >
                    {/if}
                </Label>
            </div>
        {/each}
    </div>
</Segment>
