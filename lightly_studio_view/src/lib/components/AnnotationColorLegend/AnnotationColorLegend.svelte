<script lang="ts">
    import { useColorPicker } from '$lib/hooks';
    import { useCustomLabelColors } from '$lib/hooks/useCustomLabelColors';
    import { getColorByLabel, rgbaToHex } from '$lib/utils';
    import { ColorPicker } from '../ui/color-picker';

    const {
        labelName,
        className,
        selected = false,
        testId
    }: {
        labelName: string;
        className: string;
        selected: boolean;
        testId?: string;
    } = $props();

    const { getCustomColor, hasCustomColor, customLabelColorsStore } = useCustomLabelColors();
    const picker = useColorPicker(() => labelName);

    function getInitialColor(label: string) {
        if (hasCustomColor(label)) {
            const customColor = getCustomColor(label);
            return customColor?.color || '#ff0000';
        }

        return rgbaToHex(getColorByLabel(label, 1).color) ?? '#ff0000';
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

<div class="color-picker-container" data-testid={testId}>
    <ColorPicker
        initialColor={getInitialColor(labelName)}
        initialAlpha={getInitialAlpha(labelName)}
        onChange={picker.setColor}
        onClose={picker.finishColorChange}
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
