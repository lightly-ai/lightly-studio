<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import { GroupComponents } from './';
    import Image from '../Image/Image.svelte';
    import { VideoPreview } from '../VideoPreview';
    import GroupComponent from '../GroupComponent/GroupComponent.svelte';

    const { Story } = defineMeta({
        title: 'Components/GroupComponents',
        component: GroupComponents,
        tags: ['autodocs']
    });

    const imageItems = [
        'https://picsum.photos/190?random=1',
        'https://picsum.photos/190?random=2',
        'https://picsum.photos/190?random=3',
        'https://picsum.photos/190?random=4',
        'https://picsum.photos/190?random=5'
    ];

    const videoItems = [
        'https://www.w3schools.com/html/mov_bbb.mp4',
        'https://www.w3schools.com/html/movie.mp4',
        'https://www.w3schools.com/html/mov_bbb.mp4',
        'https://www.w3schools.com/html/movie.mp4'
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
            <GroupComponent src={imageItems[index]} type="image" title={`Image ${index}`} />
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
            <GroupComponent src={videoItems[index]} type="video" title={`Video ${index}`} />
        {/snippet}
    </GroupComponents>
</Story>
