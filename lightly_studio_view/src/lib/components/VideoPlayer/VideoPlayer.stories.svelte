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

<Story
    name="Default"
    args={{
        src: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4'
    }}
/>

<Story
    name="With Controls"
    args={{
        src: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4',
        videoProps: { controls: true, muted: true, class: 'h-full w-full' }
    }}
/>

<Story name="Different Sizes" asChild>
    <div class="flex flex-col gap-4">
        <div class="h-32 w-full max-w-md">
            <VideoPlayer
                src="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
                videoProps={{
                    controls: true,
                    class: 'h-full w-full'
                }}
                hoverClass="outline outline-dashed outline-2 outline-green-500"
            />
        </div>
        <div class="h-48 w-full max-w-md">
            <VideoPlayer
                src="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
                videoProps={{ controls: true, class: 'h-full w-full' }}
                hoverClass="outline outline-dashed outline-2 outline-green-500"
            />
        </div>
        <div class="h-64 w-full max-w-md">
            <VideoPlayer
                src="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
                videoProps={{ controls: true, class: 'h-full w-full' }}
                hoverClass="outline outline-dashed outline-2 outline-green-500"
            />
        </div>
    </div>
</Story>
