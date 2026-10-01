<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import VideoPlayer from './VideoPlayer.svelte';
    import { toVideoEvents } from '$lib/utils';

    const { Story } = defineMeta({
        title: 'Components/VideoPlayer',
        component: VideoPlayer,
        tags: ['autodocs'],
        argTypes: {
            src: { control: 'text' },
            videoProps: { control: 'object' }
        }
    });

    const sampleEvents = toVideoEvents(
        [
            ['Run-up', 0, 3],
            ['Long Jump', 2, 9],
            ['Landing', 8.5, 11],
            ['Celebration', 12, 16]
        ].map(([label, start, end], index) => ({
            sample_id: `evt-${index}`,
            parent_sample_id: 'video-1',
            annotation_collection_id: 'coll-1',
            annotation_type: 'classification',
            annotation_label: { annotation_label_name: label },
            created_at: new Date(),
            temporal_span_details: { start_time_s: start, end_time_s: end }
        }))
    );
</script>

<Story name="Default" asChild>
    <div class="h-96 w-full max-w-2xl bg-black">
        <VideoPlayer
            src="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
            videoProps={{ class: 'h-full w-full object-contain' }}
        />
    </div>
</Story>

<Story name="With Events" asChild>
    <div class="h-96 w-full max-w-2xl bg-black">
        <VideoPlayer
            src="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
            videoProps={{ class: 'h-full w-full object-contain' }}
            events={sampleEvents}
            durationS={20}
        />
    </div>
</Story>

<Story name="Different Sizes" asChild>
    <div class="flex flex-col gap-4">
        <div class="h-32 w-full max-w-md bg-black">
            <VideoPlayer
                src="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
                videoProps={{ class: 'h-full w-full object-contain' }}
                hoverClass="outline outline-dashed outline-2 outline-green-500"
            />
        </div>
        <div class="h-48 w-full max-w-md bg-black">
            <VideoPlayer
                src="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
                videoProps={{ class: 'h-full w-full object-contain' }}
                hoverClass="outline outline-dashed outline-2 outline-green-500"
            />
        </div>
        <div class="h-64 w-full max-w-md bg-black">
            <VideoPlayer
                src="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
                videoProps={{ class: 'h-full w-full object-contain' }}
                hoverClass="outline outline-dashed outline-2 outline-green-500"
            />
        </div>
    </div>
</Story>
