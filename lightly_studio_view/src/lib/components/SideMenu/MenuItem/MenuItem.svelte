<script lang="ts">
    import { Checkbox } from '$lib/components/ui/checkbox/index.js';
    import { Label } from '$lib/components/ui/label/index.js';
    import type { ComponentProps } from 'svelte';
    import ColorMarker from '../ColorMarker/ColorMarker.svelte';
    import { Typography } from '$lib/components';
    import { getSegmentRowStyles } from '$lib/components/Segment/segmentDensity';
    import { cn } from '$lib/utils';

    interface Props {
        /** Label text displayed in the menu item; also used as the `title` attribute. */
        name: string;
        /** Controls the checkbox checked state. */
        checked: boolean;
        /** When `true`, renders a color swatch before the label text. */
        showColorMarker?: boolean;
        /** When `true`, the color swatch opens a color picker on click. */
        enableColorPicker?: boolean;
        /** Callback fired when the checkbox is toggled. */
        onCheckedChange: ComponentProps<typeof Checkbox>['onCheckedChange'];
    }

    let { name, checked, showColorMarker, enableColorPicker, onCheckedChange }: Props = $props();

    // Stable unique ID for pairing the checkbox and its label
    const menuItemId = $props.id();

    const rowStyles = getSegmentRowStyles();
</script>

<div title={name}>
    <div class={cn('flex w-full items-center space-x-2', rowStyles.row)}>
        <Checkbox
            id={`menu-item-${menuItemId}`}
            {checked}
            aria-labelledby={`menu-item-${menuItemId}-label`}
            class={rowStyles.checkbox}
            {onCheckedChange}
        />
        <Label
            id={`menu-item-${menuItemId}-label`}
            for={`menu-item-${menuItemId}`}
            class={cn(
                'flex min-w-0 flex-1 cursor-pointer items-center gap-2 text-nowrap peer-disabled:cursor-not-allowed peer-disabled:opacity-70',
                rowStyles.label
            )}
        >
            {#if showColorMarker}
                <ColorMarker
                    label={name}
                    {enableColorPicker}
                    markerProps={{ 'data-testid': `color-marker-${name}` }}
                />
            {/if}
            <Typography variant="body1" className={cn('flex-1 truncate', rowStyles.label)}>
                {name}
            </Typography>
        </Label>
    </div>
</div>
