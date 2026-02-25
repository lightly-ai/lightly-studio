<script lang="ts">
    import { useCustomLabelColors } from '$lib/hooks/useCustomLabelColors';
    import { getColorByLabel } from '$lib/utils';
    import { ColorPicker } from '../ui/color-picker';

    const {
        labelName,
        className,
        selected = false
    }: {
        labelName: string;
        className: string;
        selected: boolean;
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

<div class="color-picker-container">
    <ColorPicker
        initialColor={getInitialColor(labelName)}
        initialAlpha={getInitialAlpha(labelName)}
        onChange={(color, alpha) => handleColorChange(labelName, color, alpha)}
    >
        <div
            class={`${className} cursor-pointer rounded-sm border`}
            style={`
                                    border-color: ${
                                        colorInfos[labelName]?.borderColor ??
                                        getColorByLabel(labelName).color
                                    };
                                    background-color: ${
                                        colorInfos[labelName]?.backgroundColor ??
                                        getColorByLabel(labelName, selected ? 1 : 0.4).color
                                    };
                                `}
        ></div>
    </ColorPicker>
</div>
