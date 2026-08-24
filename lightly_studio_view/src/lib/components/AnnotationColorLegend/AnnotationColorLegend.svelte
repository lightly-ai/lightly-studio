<script lang="ts">
    import { useColorPicker } from '$lib/hooks';
    import { useCustomLabelColors } from '$lib/hooks/useCustomLabelColors';
    import { getColorByLabel, rgbaToHex } from '$lib/utils';
    import { Pencil } from '@lucide/svelte';
    import { ColorPicker } from '../ui/color-picker';
    import { Tooltip } from '../ui/tooltip';

    const {
        labelName,
        className,
        selected = false,
        variant = 'swatch',
        ariaLabel,
        testId
    }: {
        labelName: string;
        className: string;
        selected: boolean;
        /**
         * `swatch` shows the class color as a filled square (also the color-picker trigger).
         * `edit` shows a pencil that only opens the picker — used where the color is already
         * carried by another control (e.g. a colored checkbox) so the square would be redundant.
         */
        variant?: 'swatch' | 'edit';
        ariaLabel?: string;
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

    const borderColor = $derived(
        colorInfos[labelName]?.borderColor ?? getColorByLabel(labelName).color
    );
    const backgroundColor = $derived(
        colorInfos[labelName]?.backgroundColor ??
            getColorByLabel(labelName, selected ? 1 : 0.4).color
    );
</script>

{#snippet pickerTrigger()}
    <div class="color-picker-container" data-testid={testId}>
        <ColorPicker
            initialColor={getInitialColor(labelName)}
            initialAlpha={getInitialAlpha(labelName)}
            onChange={picker.setColor}
            onClose={picker.finishColorChange}
            {ariaLabel}
        >
            {#if variant === 'edit'}
                <Pencil class={`${className} cursor-pointer`} style={`color: ${borderColor};`} />
            {:else}
                <div
                    class={`${className} cursor-pointer rounded-sm border`}
                    style={`border-color: ${borderColor}; background-color: ${backgroundColor};`}
                ></div>
            {/if}
        </ColorPicker>
    </div>
{/snippet}

{#if variant === 'edit'}
    <!-- Reveal on row hover / keyboard focus, matching the sibling visibility toggle. -->
    <Tooltip
        content="Change class color"
        triggerClass="opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100"
    >
        {@render pickerTrigger()}
    </Tooltip>
{:else}
    {@render pickerTrigger()}
{/if}
