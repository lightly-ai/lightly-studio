<script lang="ts">
    import AnnotationColorLegend from '$lib/components/AnnotationColorLegend/AnnotationColorLegend.svelte';

    interface Props {
        className: string;
    }

    let { className }: Props = $props();
</script>

<AnnotationColorLegend
    labelName={className}
    className="h-3 w-3"
    selected
    testId="label-color-legend"
    enableColorPicker={false}
/>
