<script lang="ts">
    import type { TickTagView, TickView } from '$lib/api/lightly_studio_local/types.gen';
    import { TimelineLane } from '../TimelineViewport';
    import { buildTagRuns, type TagRun } from './buildTagRuns';

    /** One row per frame tag, with a bar over each run of tagged ticks. */
    interface Props {
        ticks: TickView[];
        tags: TickTagView[];
        /** Called with the first tick of a clicked bar. */
        onSelectTick: (seqNumber: number) => void;
    }

    let { ticks, tags, onSelectTick }: Props = $props();

    const rows = $derived(tags.map((tag) => ({ tag, runs: buildTagRuns(ticks, tag.seq_numbers) })));

    const runTitle = (tagName: string, run: TagRun) =>
        run.startIndex === run.endIndex
            ? `${tagName} · Frame ${run.startIndex + 1}`
            : `${tagName} · Frames ${run.startIndex + 1}–${run.endIndex + 1}`;
</script>

{#if rows.length > 0}
    <div class="px-1" data-testid="frame-tag-rows" data-timeline-body>
        {#each rows as { tag, runs } (tag.tag_id)}
            <div class="py-1">
                <div
                    class="sticky left-3 w-fit max-w-xs truncate pb-0.5 text-[10px] text-muted-foreground"
                    title={tag.name}
                    data-testid="tag-row-label"
                >
                    {tag.name}
                </div>
                <TimelineLane>
                    <div class="relative h-3 w-full overflow-hidden rounded-sm bg-muted/40">
                        {#each runs as run (run.startIndex)}
                            <button
                                type="button"
                                class="absolute inset-y-0 cursor-pointer bg-muted-foreground/60 hover:bg-muted-foreground/80"
                                style:left={`${(run.startIndex / ticks.length) * 100}%`}
                                style:width={`${((run.endIndex - run.startIndex + 1) / ticks.length) * 100}%`}
                                title={runTitle(tag.name, run)}
                                aria-label={runTitle(tag.name, run)}
                                onclick={() => onSelectTick(ticks[run.startIndex].seq_number)}
                            ></button>
                        {/each}
                    </div>
                </TimelineLane>
            </div>
        {/each}
    </div>
{/if}
