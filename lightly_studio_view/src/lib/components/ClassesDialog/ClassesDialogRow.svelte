<script lang="ts">
    import type { AnnotationLabelWithCountView } from '$lib/api/lightly_studio_local';
    import AnnotationColorLegend from '$lib/components/AnnotationColorLegend/AnnotationColorLegend.svelte';

    let { label }: { label: AnnotationLabelWithCountView } = $props();
</script>

<tr>
    <td class="w-16 py-2 pl-3">
        <AnnotationColorLegend
            labelName={label.annotation_label_name}
            className="size-4"
            selected={false}
        />
    </td>
    <td class="max-w-0 truncate py-2" title={label.annotation_label_name}>
        {label.annotation_label_name}
    </td>
    <td class="w-20 py-2 text-center tabular-nums">{label.annotation_count}</td>
</tr>
