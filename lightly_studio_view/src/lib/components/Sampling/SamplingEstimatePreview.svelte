<script lang="ts">
    import type { SamplingEstimate } from './samplingEstimate';
    import { formatDuration, formatRange } from './samplingEstimate';

    interface Props {
        estimate: SamplingEstimate;
    }

    const { estimate }: Props = $props();
</script>

<div
    class="rounded-md border border-border bg-muted/30 p-3 text-sm"
    data-testid="sampling-dialog-estimate-preview"
>
    <p>
        Estimated sampling time:
        <strong>~{formatRange(estimate.runtimeSeconds, formatDuration)}</strong>
    </p>
</div>
