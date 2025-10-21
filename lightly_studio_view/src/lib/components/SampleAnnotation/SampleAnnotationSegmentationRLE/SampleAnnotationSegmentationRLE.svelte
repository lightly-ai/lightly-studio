<script lang="ts">
    import calculateBinaryMaskFromRLE from './calculateBinaryMaskFromRLE/calculateBinaryMaskFromRLE';

    const {
        width,
        segmentation,
        colorFill = 'rgba(255, 0, 0, 0.2)',
        opacity = 0.4
    }: {
        width: number;
        segmentation: number[];
        colorFill?: string;
        opacity?: number;
    } = $props();

    if (!segmentation) {
        throw new Error('Segmentation data is required');
    }

    // Convert the segmentation to a binary mask image.
    const { dataUrl: maskDataUrl, height } = $derived.by(() => {
        const opaqueColor = colorFill.replace(
            /rgba?\((\d+,\s*\d+,\s*\d+)(?:,\s*[\d.]+)?\)/,
            'rgb($1)'
        );

        return calculateBinaryMaskFromRLE(segmentation, width, opaqueColor);
    });
</script>

<image href={maskDataUrl} x="0" y="0" {width} {height} {opacity} />
