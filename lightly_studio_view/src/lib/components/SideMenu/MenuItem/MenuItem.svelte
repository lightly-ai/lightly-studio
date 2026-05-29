<script lang="ts">
    import { Checkbox } from '$lib/components/ui/checkbox/index.js';
    import { Label } from '$lib/components/ui/label/index.js';
    import type { ComponentProps } from 'svelte';
    import ColorMarker from '../ColorMarker/ColorMarker.svelte';
    import { Typography } from '$lib/components';
    import { ColorPicker } from '$lib/components/ui/color-picker';

    interface Props {
        /** Label text displayed in the menu item; also used as the `title` attribute. */
        name: string;
        /** Controls the checkbox checked state. */
        checked: boolean;
        /** When `true`, renders a color swatch before the label text. */
        showColorMarker?: boolean;
        /** Explicit hex color for the swatch; falls back to label-based computation. */
        color?: string;
        /** When provided, the swatch becomes a color picker trigger. */
        onColorChange?: (color: string) => void;
        /** Callback fired when the checkbox is toggled. */
        onCheckedChange: ComponentProps<typeof Checkbox>['onCheckedChange'];
    }

    let { name, checked, showColorMarker, color, onColorChange, onCheckedChange }: Props =
        $props();

    // Stable unique ID for pairing the checkbox and its label
    const menuItemId = $props.id();
</script>

<div class="space-y-1" title={name}>
    <div class="flex w-full items-center space-x-2">
        <Checkbox
            id={`menu-item-${menuItemId}`}
            {checked}
            aria-labelledby={`menu-item-${menuItemId}-label`}
            {onCheckedChange}
        />
        <Label
            id={`menu-item-${menuItemId}-label`}
            for={`menu-item-${menuItemId}`}
            class="flex min-w-0 flex-1 cursor-pointer items-center space-x-2 text-nowrap peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
        >
            {#if showColorMarker}
                {#if onColorChange}
                    <ColorPicker
                        initialColor={color}
                        onChange={(c) => onColorChange(c)}
                        position="right"
                    >
                        <ColorMarker
                            label={name}
                            {color}
                            markerProps={{
                                'data-testid': `color-marker-${name}`,
                                class: 'cursor-pointer hover:opacity-80 transition-opacity'
                            }}
                        />
                    </ColorPicker>
                {:else}
                    <ColorMarker
                        label={name}
                        {color}
                        markerProps={{ 'data-testid': `color-marker-${name}` }}
                    />
                {/if}
            {/if}
            <Typography variant="body1" className="flex-1 truncate">
                {name}
            </Typography>
        </Label>
    </div>
</div>
