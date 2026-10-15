<script module lang="ts">
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import TimelineBuffer from './TimelineBuffer.svelte';

    const { Story } = defineMeta({
        title: 'Components/PointCloudLabelingWorkspace/FrameTimeline/TimelineBuffer',
        component: TimelineBuffer,
        tags: ['autodocs'],
        parameters: { layout: 'centered' },
        args: {
            tickCount: 20,
            bufferedRanges: [{ startIndex: 0, endIndex: 5 }]
        }
    });
</script>

{#snippet buffer(args)}
    <div class="relative h-4 w-[32rem] rounded bg-muted/50">
        <TimelineBuffer {...args} />
    </div>
{/snippet}

<Story
    name="Continuous buffer"
    template={buffer}
    parameters={{
        docs: {
            description: {
                story: 'Shows a continuous range of ticks already loaded ahead of playback.'
            }
        }
    }}
/>

<Story
    name="Buffered ranges with a gap"
    args={{
        bufferedRanges: [
            { startIndex: 1, endIndex: 3 },
            { startIndex: 7, endIndex: 9 }
        ]
    }}
    template={buffer}
/>

<Story name="Nothing buffered yet" args={{ bufferedRanges: [] }} template={buffer} />
