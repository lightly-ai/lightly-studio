<script lang="ts">
    import { useClassColorPicker } from '$lib/hooks';
    import { useCustomLabelColors } from '$lib/hooks/useCustomLabelColors';
    import { getColorByLabel } from '$lib/utils';
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

    const { customLabelColorsStore } = useCustomLabelColors();
    const picker = useClassColorPicker(() => labelName);

    const colorInfos = $derived.by(() => {
        const colors = $customLabelColorsStore;
        const out: Record<string, { borderColor: string; backgroundColor: string }> = {};

        for (const label of Object.keys(colors)) {
            const custom = colors[label];
            out[label] = {
                borderColor: custom.color,
                backgroundColor: getColorByLabel(label, selected ? 1 : 0.4).color
            };
        }
        return out;
    });
</script>

<div class="color-picker-container" data-testid={testId}>
    <ColorPicker
        initialColor={picker.initialColor}
        initialAlpha={picker.initialAlpha}
        triggerLabel={`Change the color of ${labelName}`}
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
