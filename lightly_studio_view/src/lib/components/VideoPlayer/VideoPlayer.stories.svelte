<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import VideoPlayer from './VideoPlayer.svelte';

    const { Story } = defineMeta({
        title: 'Components/VideoPlayer',
        component: VideoPlayer,
        tags: ['autodocs'],
        argTypes: {
            src: { control: 'text' },
            controls: { control: 'boolean' },
            muted: { control: 'boolean' },
            playsinline: { control: 'boolean' },
            preload: {
                control: 'select',
                options: ['auto', 'metadata', 'none']
            },
            className: { control: 'text' }
        }
    });
</script>

<Story
    name="Default"
    args={{
        src: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4',
        controls: true
    }}
/>

<Story
    name="With Controls"
    args={{
        src: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4',
        controls: true,
        muted: true
    }}
/>

<Story
    name="Unmuted with Controls"
    args={{
        src: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4',
        controls: true,
        muted: false
    }}
/>

<Story
    name="Custom Size"
    args={{
        src: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4',
        controls: true,
        className: 'h-96 w-96'
    }}
/>

<Story
    name="No Controls"
    args={{
        src: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4',
        controls: false
    }}
/>

<Story name="Multiple Players" asChild>
    <div class="flex gap-4">
        <div class="h-64 w-64">
            <VideoPlayer
                src="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
                controls={true}
                className="h-full w-full"
            />
        </div>
        <div class="h-64 w-64">
            <VideoPlayer
                src="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4"
                controls={true}
                className="h-full w-full"
            />
        </div>
    </div>
</Story>

<Story name="Different Sizes" asChild>
    <div class="flex flex-col gap-4">
        <div class="h-32 w-full max-w-md">
            <VideoPlayer
                src="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
                controls={true}
                className="h-full w-full"
            />
        </div>
        <div class="h-48 w-full max-w-md">
            <VideoPlayer
                src="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
                controls={true}
                className="h-full w-full"
            />
        </div>
        <div class="h-64 w-full max-w-md">
            <VideoPlayer
                src="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
                controls={true}
                className="h-full w-full"
            />
        </div>
    </div>
</Story>
