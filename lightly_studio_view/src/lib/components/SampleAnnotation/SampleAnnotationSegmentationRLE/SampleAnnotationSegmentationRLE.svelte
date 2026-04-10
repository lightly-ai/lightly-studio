<script lang="ts">
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

        const opaqueColor = colorFill.replace(
            /rgba?\((\d+,\s*\d+,\s*\d+)(?:,\s*[\d.]+)?\)/,
            'rgb($1)'
        );

        return calculateBinaryMaskFromRLE(segmentation, width, opaqueColor);
    });
</script>

<image href={maskDataUrl} x="0" y="0" {width} {height} {opacity} pointer-events="none" />
