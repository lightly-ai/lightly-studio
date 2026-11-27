<script lang="ts">
    import { Typography } from '$lib/components/Typography';
    import { formatDistance } from '$lib/components/PointCloudLabelingWorkspace/EgoRange';

    interface Props {
        meters: number;
        isBeyondRange: boolean;
    }

    let { meters, isBeyondRange }: Props = $props();
</script>

<div class="grid grid-cols-[5rem_1fr] gap-x-2">
    <Typography component="dt" variant="body2">Ego distance:</Typography>
    <Typography component="dd" variant="body2">
        <span data-testid="point-cloud-annotation-distance">
            {formatDistance(meters)}
            {#if isBeyondRange}
                <span class="ml-1 rounded bg-muted px-1 text-xs text-muted-foreground"
                    >beyond range</span
                >
            {/if}
        </span>
    </Typography>
</div>
