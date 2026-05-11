<script lang="ts">
    import { Checkbox } from '$lib/components/ui/checkbox/index.js';
    import { Label } from '$lib/components/ui/label/index.js';
    import type { ComponentProps } from 'svelte';
    import ColorMarker from '../ColorMarker/ColorMarker.svelte';
    import { Typography } from '$lib/components';

    interface Props {
        /** Label text displayed in the menu item; also used as the `title` attribute and checkbox `id`. */
        name: string;
        /** Controls the checkbox checked state. */
        checked: boolean;
        /** When `true`, renders a color swatch before the label text. */
        showColorMarker?: boolean;
        /** Callback fired when the checkbox is toggled. */
        onCheckedChange: ComponentProps<typeof Checkbox>['onCheckedChange'];
    }

    let { name, checked, showColorMarker, onCheckedChange }: Props = $props();

    // Get a unique ID for the checkbox and label
    const nameId = Math.random().toString(36);
</script>

<div class="space-y-1" title={name}>
    <div class="flex w-full items-center space-x-2">
        <Checkbox
            id={`menu-item-${nameId}`}
            {checked}
            aria-labelledby={`menu-item-${nameId}-label`}
            {onCheckedChange}
        />
        <Label
            id={`menu-item-${nameId}-label`}
            for={`menu-item-${nameId}`}
            class="flex min-w-0 flex-1 cursor-pointer items-center space-x-2 text-nowrap peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
        >
            {#if showColorMarker}
                <ColorMarker label={name} markerProps={{ 'data-testid': `color-marker-${name}` }} />
            {/if}
            <Typography variant="body1" className="flex-1 truncate">
                {name}
            </Typography>
        </Label>
    </div>
</div>
