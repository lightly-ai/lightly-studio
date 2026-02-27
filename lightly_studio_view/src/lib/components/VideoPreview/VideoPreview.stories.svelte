<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import { VideoPreview } from './';

    const { Story } = defineMeta({
        title: 'Components/VideoPreview',
        component: VideoPreview,
        tags: ['autodocs']
    });
</script>

<Story name="Default" asChild>
    <VideoPreview src="https://www.w3schools.com/html/mov_bbb.mp4" />
</Story>

<Story name="Custom Size" asChild>
    <VideoPreview src="https://www.w3schools.com/html/movie.mp4" className="h-64 w-64" />
</Story>

<Story name="Multiple Previews" asChild>
    <div class="flex gap-4">
        <VideoPreview src="https://www.w3schools.com/html/mov_bbb.mp4" className="h-40 w-40" />
        <VideoPreview src="https://www.w3schools.com/html/movie.mp4" className="h-40 w-40" />
        <VideoPreview src="https://www.w3schools.com/html/mov_bbb.mp4" className="h-40 w-40" />
    </div>
</Story>
