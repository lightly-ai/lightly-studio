<script lang="ts">
    import { Alert, AlertDescription, AlertTitle } from '$lib/components/ui/alert';
    import { onMount } from 'svelte';
    import BenchmarkControls from './BenchmarkControls.svelte';
    import { runBenchmark } from './benchmark';
    import BenchmarkResults from './BenchmarkResults.svelte';
    import {
        loadBackendFrame,
        loadBrowserFrame,
        resetBackendPath,
        resetBrowserPath
    } from './loadFrames';
    import PointCloudCanvas from './PointCloudCanvas.svelte';
    import type { BenchmarkResult, McapSource, PointCloudFrame, ProcessingPath } from './types';

    const NANOSECONDS_PER_SECOND = 1_000_000_000;

    let source = $state<McapSource>();
    let topic = $state('');
    let timestampNs = $state('');
    let runs = $state(5);
    let stepSeconds = $state(1);
    let completed = $state(0);
    let result = $state<BenchmarkResult>();
    let displayedFrame = $state<PointCloudFrame>();
    let running = $state(false);
    let error = $state('');

    onMount(() => void loadSource());

    async function loadSource(): Promise<void> {
        try {
            const response = await fetch('/api/mcap-poc/source', { cache: 'no-store' });
            if (!response.ok) throw new Error(await response.text());
            source = await response.json();
            topic = source?.topics[0]?.topic ?? '';
            timestampNs = source?.topics[0]?.first_log_time_ns ?? '';
        } catch (caught) {
            error = message(caught);
        }
    }

    async function run(paths: ProcessingPath[]): Promise<void> {
        if (!source || !topic || !timestampNs) return;
        running = true;
        error = '';
        completed = 0;
        try {
            result = await runBenchmark({
                runs: Math.max(1, Math.round(runs)),
                paths,
                startTimestampNs: timestampNs,
                stepNs: BigInt(Math.round(stepSeconds * NANOSECONDS_PER_SECOND)),
                load: loadFrame,
                onIteration: (iteration) => {
                    displayedFrame = iteration.frames.browser ?? iteration.frames.backend;
                    completed += 1;
                }
            });
        } catch (caught) {
            error = message(caught);
        } finally {
            running = false;
        }
    }

    function loadFrame(path: ProcessingPath, at: string): Promise<PointCloudFrame> {
        if (!source) throw new Error('The MCAP source is not loaded.');
        return path === 'browser'
            ? loadBrowserFrame(source, topic, at)
            : loadBackendFrame(topic, at);
    }

    async function reset(): Promise<void> {
        error = '';
        result = undefined;
        resetBrowserPath();
        try {
            await resetBackendPath();
        } catch (caught) {
            error = message(caught);
        }
    }

    const message = (caught: unknown): string =>
        caught instanceof Error ? caught.message : String(caught);
</script>

<main class="mx-auto flex w-full max-w-[1600px] flex-1 flex-col gap-5 overflow-auto p-6">
    <div>
        <p class="text-sm font-medium text-primary">LIG-10610 proof of concept</p>
        <h1 class="text-2xl font-semibold">MCAP point-cloud processing comparison</h1>
        <p class="mt-1 text-sm text-muted-foreground">
            Compare browser range reads and Web Worker decoding with backend on-demand decoding.
        </p>
    </div>
    {#if error}
        <Alert variant="destructive">
            <AlertTitle>Could not run benchmark</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
        </Alert>
    {/if}
    {#if source}
        <BenchmarkControls
            topics={source.topics}
            bind:topic
            bind:timestampNs
            bind:runs
            bind:stepSeconds
            {running}
            {completed}
            onrun={run}
            onreset={reset}
        />
        <BenchmarkResults {result} {source} {topic} />
        <PointCloudCanvas frame={displayedFrame} />
    {:else if !error}
        <p class="text-sm text-muted-foreground">Loading the configured MCAP source…</p>
    {/if}
</main>
