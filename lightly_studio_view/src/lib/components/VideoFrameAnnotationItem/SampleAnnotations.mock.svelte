<script lang="ts">
    interface Props {
        outputWidth?: number;
        outputHeight?: number;
        objectFit?: string;
    }

    let { outputWidth, outputHeight, objectFit }: Props = $props();
</script>

<div
    data-testid="mock-video-sample-annotations"
    data-output-width={outputWidth}
    data-output-height={outputHeight}
    data-object-fit={objectFit}
></div>
