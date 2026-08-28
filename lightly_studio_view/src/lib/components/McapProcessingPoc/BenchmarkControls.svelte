<script lang="ts">
    import { Button } from '$lib/components/ui/button';
    import { Input } from '$lib/components/ui/input';
    import { Label } from '$lib/components/ui/label';
    import type { McapTopic, ProcessingPath } from './types';

    let {
        topics,
        topic = $bindable(),
        timestampNs = $bindable(),
        runs = $bindable(),
        stepSeconds = $bindable(),
        running,
        completed,
        onrun,
        onreset
    }: {
        topics: McapTopic[];
        topic: string;
        timestampNs: string;
        runs: number;
        stepSeconds: number;
        running: boolean;
        completed: number;
        onrun: (paths: ProcessingPath[]) => void;
        onreset: () => void;
    } = $props();
</script>

<div class="grid gap-4 rounded-lg border bg-card p-4">
    <div class="grid gap-4 lg:grid-cols-[2fr_1fr_auto_auto]">
        <div class="grid gap-2">
            <Label for="mcap-topic">Point-cloud topic</Label>
            <select
                id="mcap-topic"
                class="h-10 rounded-md border border-input bg-background px-3 text-sm"
                bind:value={topic}
            >
                {#each topics as item}
                    <option value={item.topic}>{item.topic} ({item.message_count} frames)</option>
                {/each}
            </select>
        </div>
        <div class="grid gap-2">
            <Label for="mcap-timestamp">Start timestamp (ns)</Label>
            <Input id="mcap-timestamp" bind:value={timestampNs} />
        </div>
        <div class="grid gap-2">
            <Label for="mcap-runs">Runs</Label>
            <Input id="mcap-runs" type="number" min="1" max="50" bind:value={runs} />
        </div>
        <div class="grid gap-2">
            <Label for="mcap-step">Step (s)</Label>
            <Input id="mcap-step" type="number" min="0" step="0.1" bind:value={stepSeconds} />
        </div>
    </div>
    <div class="flex flex-wrap items-center gap-2">
        <Button disabled={running} onclick={() => onrun(['browser', 'backend'])}>Run both</Button>
        <Button variant="outline" disabled={running} onclick={() => onrun(['browser'])}>
            Browser only
        </Button>
        <Button variant="outline" disabled={running} onclick={() => onrun(['backend'])}>
            Backend only
        </Button>
        <Button variant="ghost" disabled={running} onclick={onreset}>Drop cached indexes</Button>
        {#if running}
            <span class="text-sm text-muted-foreground">Run {completed + 1} of {runs}…</span>
        {/if}
    </div>
    <p class="text-sm text-muted-foreground">
        The first run of each path also parses the summary index and is reported separately. Every
        later run advances the timestamp by the step so the comparison is not dominated by one hot
        frame.
    </p>
</div>
