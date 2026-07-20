<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import VideoPlayer from './VideoPlayer.svelte';

    const { Story } = defineMeta({
        title: 'Components/VideoPlayer',
        component: VideoPlayer,
        tags: ['autodocs'],
        argTypes: {
            src: { control: 'text' },
            videoProps: { control: 'object' }
        }
    });
</script>

<Story name="Default" asChild>
    <div class="h-96 w-full max-w-2xl bg-black">
        <VideoPlayer
            src="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
            videoProps={{ class: 'h-full w-full object-contain' }}
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
