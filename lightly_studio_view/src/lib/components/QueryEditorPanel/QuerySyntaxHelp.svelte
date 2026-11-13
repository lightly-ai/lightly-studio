<script lang="ts">
    import Typography from '$lib/components/Typography/Typography.svelte';

    interface Props {
        sampleType: 'image' | 'video';
    }
    const { sampleType }: Props = $props();
</script>

<Typography
    variant="body2"
    component="div"
    className="mt-1 min-w-0 break-words text-muted-foreground [&_code]:break-all"
>
    <p>Write a query expression to filter your dataset. Available syntax:</p>
    <ul class="my-1 ml-4 list-disc space-y-1">
        <li>Logical operations: <code>AND</code>, <code>OR</code>, <code>NOT</code></li>
        <li>
            {sampleType === 'video' ? 'Video' : 'Image'} fields: <code>file_name</code>,
            <code>file_path_abs</code>, <code>width</code>, <code>height</code>,
            {#if sampleType === 'video'}
                <code>duration_s</code>, <code>fps</code> (equality only).
            {:else}
                <code>created_at</code>
            {/if}
        </li>
        <li>Metadata: <code>metadata["quality_score"] &gt;= 0.8</code></li>
        <li>
            Sample evaluation: <code>sample_evaluation(name = "run-name" AND "tp" &gt;= 1)</code>
        </li>
        <li>Tag membership: <code>"tag_name" IN tags</code></li>
        <li>
            {#if sampleType === 'video'}
                Video annotations: <code>classification(…)</code> matches whole-video and temporal annotations.
                Frame annotations are not supported yet.
            {:else}
                Annotation conditions: <code>segmentation_mask(…)</code>,
                <code>object_detection(…)</code>, <code>classification(…)</code>
            {/if}
        </li>
    </ul>
    <p>Tip: Completion hints will appear as you type a space or a left parenthesis.</p>
</Typography>
