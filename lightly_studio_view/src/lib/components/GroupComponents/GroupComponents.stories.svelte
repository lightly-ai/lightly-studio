<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import { GroupComponents } from './';
    import Image from '../Image/Image.svelte';
    import { VideoPreview } from '../VideoPreview';

    const { Story } = defineMeta({
        title: 'Components/GroupComponents',
        component: GroupComponents,
        tags: ['autodocs']
    });

    const imageItems = [
        { src: 'https://picsum.photos/190?random=1', type: 'image' },
        { src: 'https://picsum.photos/190?random=2', type: 'image' },
        { src: 'https://picsum.photos/190?random=3', type: 'image' },
        { src: 'https://picsum.photos/190?random=4', type: 'image' },
        { src: 'https://picsum.photos/190?random=5', type: 'image' }
    ];

    const videoItems = [
        { src: 'https://www.w3schools.com/html/mov_bbb.mp4', type: 'video' },
        { src: 'https://www.w3schools.com/html/movie.mp4', type: 'video' },
        { src: 'https://www.w3schools.com/html/mov_bbb.mp4', type: 'video' },
        { src: 'https://www.w3schools.com/html/movie.mp4', type: 'video' }
    ];
</script>

<script>
    let selectedImageIndex = $state(1);
    let selectedVideoIndex = $state(0);
</script>

<Story name="Images" asChild>
    <GroupComponents
        itemsCount={imageItems.length}
        selectedIndex={selectedImageIndex}
        onclick={(index) => (selectedImageIndex = index)}
    >
        {#snippet renderItem({ index })}
            <Image src={imageItems[index].src} />
        {/snippet}
    </GroupComponents>
</Story>

<Story name="Videos" asChild>
    <GroupComponents
        itemsCount={videoItems.length}
        selectedIndex={selectedVideoIndex}
        onclick={(index) => (selectedVideoIndex = index)}
    >
        {#snippet renderItem({ index })}
            <VideoPreview src={videoItems[index].src} />
        {/snippet}
    </GroupComponents>
</Story>
