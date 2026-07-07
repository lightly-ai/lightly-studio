<script lang="ts">
    import { stripAlpha } from '$lib/utils';
    import calculateBinaryMaskFromRLE from './calculateBinaryMaskFromRLE/calculateBinaryMaskFromRLE';

    const {
        width,
        segmentation,
        colorFill = 'rgba(255, 0, 0, 0.2)',
        opacity = 0.4,
        prerenderedDataUrl,
        prerenderedHeight
    }: {
        width: number;
        segmentation: number[];
        colorFill?: string;
        opacity?: number;
        prerenderedDataUrl?: string;
        prerenderedHeight?: number;
    } = $props();

    if (!segmentation) {
        throw new Error('Segmentation data is required');
    }

    // Use prerendered data URL if available, otherwise calculate from segmentation
    const { dataUrl: maskDataUrl, height } = $derived.by(() => {
        if (prerenderedDataUrl && prerenderedHeight !== undefined) {
            return { dataUrl: prerenderedDataUrl, height: prerenderedHeight };
        }

        return calculateBinaryMaskFromRLE(segmentation, width, stripAlpha(colorFill));
    });
</script>

<image href={maskDataUrl} x="0" y="0" {width} {height} {opacity} pointer-events="none" />
