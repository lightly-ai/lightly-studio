<script lang="ts">
    import { LoaderCircle } from '@lucide/svelte';
    import type { FrozenSamplingRun } from './samplingEstimate';
    import {
        estimateFinish,
        formatDuration,
        formatLocalTime,
        formatRange
    } from './samplingEstimate';

    interface Props {
        run: FrozenSamplingRun;
        loadingMessage: string;
    }

    const { run, loadingMessage }: Props = $props();
    const showSeconds = run.estimate.runtimeSeconds.premium < 60;
    const finish = estimateFinish(run);
</script>

<div class="grid gap-4 py-4" data-testid="sampling-dialog-running">
    <div class="flex items-center gap-2">
        <LoaderCircle class="size-5 animate-spin text-primary" />
        <p class="font-medium">{loadingMessage || 'Creating selection...'}</p>
    </div>
    <dl class="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
        <dt class="text-muted-foreground">Started</dt>
        <dd data-testid="sampling-dialog-started-at">
            {formatLocalTime(run.startedAt, showSeconds)}
        </dd>
        <dt class="text-muted-foreground">Expected duration</dt>
        <dd data-testid="sampling-dialog-expected-duration">
            ~{formatRange(run.estimate.runtimeSeconds, formatDuration)}
        </dd>
        <dt class="text-muted-foreground">Estimated finish</dt>
        <dd data-testid="sampling-dialog-estimated-finish">
            {formatLocalTime(finish, showSeconds)}
        </dd>
    </dl>
    <p class="text-xs text-muted-foreground">
        This is only a rough estimate. Actual time may vary significantly.
    </p>
</div>
