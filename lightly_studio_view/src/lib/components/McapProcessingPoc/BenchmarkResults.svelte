<script lang="ts">
    import { Button } from '$lib/components/ui/button';
    import { toMarkdown } from './benchmark';
    import type { BenchmarkResult, McapSource, MetricSummary, ProcessingPath } from './types';

    let { result, source, topic }: { result?: BenchmarkResult; source: McapSource; topic: string } =
        $props();

    const paths: ProcessingPath[] = ['browser', 'backend'];
    let copied = $state(false);

    const rows = $derived(
        paths
            .map((path) => ({ path, summary: result?.summaries[path] }))
            .filter((row) => row.summary !== undefined)
    );

    const format = (value: number | undefined, scale = 1): string =>
        value === undefined
            ? '—'
            : (value * scale).toLocaleString('en-US', { maximumFractionDigits: 1 });

    const spread = (summary: MetricSummary | undefined, scale = 1): string =>
        summary === undefined
            ? '—'
            : `${format(summary.median, scale)} (${format(summary.min, scale)}–${format(summary.max, scale)})`;

    async function copyMarkdown(): Promise<void> {
        if (!result) return;
        const markdown = toMarkdown(result, { source, topic });
        try {
            await navigator.clipboard.writeText(markdown);
            copied = true;
            setTimeout(() => (copied = false), 2000);
        } catch {
            // Clipboard access needs a secure context; fall back to the console.
            console.info(markdown);
        }
    }
</script>

<div class="overflow-hidden rounded-lg border">
    <div class="overflow-x-auto">
        <table class="w-full text-left text-sm">
            <thead class="border-b bg-muted/50">
                <tr>
                    <th class="p-3">Path</th>
                    <th class="p-3">Cold total ms</th>
                    <th class="p-3">Total ms</th>
                    <th class="p-3">Processing ms</th>
                    <th class="p-3">Decode ms</th>
                    <th class="p-3">Source KB</th>
                    <th class="p-3">Reads</th>
                    <th class="p-3">Peak MB</th>
                </tr>
            </thead>
            <tbody>
                {#each rows as { path, summary }}
                    <tr class="border-b last:border-0">
                        <th class="p-3 font-medium capitalize">
                            {path}
                            <span class="block font-normal text-muted-foreground">
                                {summary?.runs} warm runs
                            </span>
                        </th>
                        <td class="p-3">{format(summary?.coldTotalMs)}</td>
                        <td class="p-3">{spread(summary?.totalMs)}</td>
                        <td class="p-3">{spread(summary?.processingMs)}</td>
                        <td class="p-3">{spread(summary?.decodeMs)}</td>
                        <td class="p-3">{spread(summary?.bytesRead, 1 / 1024)}</td>
                        <td class="p-3">{spread(summary?.requestCount)}</td>
                        <td class="p-3">{spread(summary?.peakMemoryBytes, 1e-6)}</td>
                    </tr>
                {/each}
                {#if rows.length === 0}
                    <tr>
                        <td class="p-3 text-muted-foreground" colspan="8">
                            No runs yet. Medians are shown with their minimum and maximum.
                        </td>
                    </tr>
                {/if}
            </tbody>
        </table>
    </div>
    {#if result && result.compared > 0}
        <div class="flex flex-wrap items-center justify-between gap-2 border-t p-3 text-sm">
            <span>
                Identical frames:
                <strong>{result.matched}/{result.compared}</strong>
                · both paths compared by log time and point count
            </span>
            <Button variant="outline" size="sm" onclick={copyMarkdown}>
                {copied ? 'Copied' : 'Copy as markdown'}
            </Button>
        </div>
    {/if}
</div>
