<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import GridItem from './GridItem.svelte';

    const { Story } = defineMeta({
        title: 'Components/GridItem',
        component: GridItem,
        tags: ['autodocs'],
        args: {
            width: 300,
            height: 300,
            tag: false
        },
        argTypes: {
            width: { control: 'number' },
            height: { control: 'number' },
            caption: { control: 'text' },
            isSelected: { control: 'boolean' },
            tag: { control: 'boolean' }
        }
    });
</script>

<Story name="Image Item Without Captions">
    <img
        src="https://picsum.photos/300?random=1"
        alt="Sample 1"
        class="h-full w-full object-cover"
    />
</Story>

<Story name="Image Item" args={{ caption: 'sample-image.jpg' }}>
    <img
        src="https://picsum.photos/300?random=1"
        alt="Sample 1"
        class="h-full w-full object-cover"
    />
</Story>

<Story name="Selected Item" args={{ caption: 'selected-item.jpg', isSelected: true }}>
    <img
        src="https://picsum.photos/300?random=2"
        alt="Selected sample"
        class="h-full w-full object-cover"
    />
</Story>

<Story name="Video Item">
    <video autoplay muted loop class="h-full w-full object-cover" title="Video sample preview">
        <source
            src="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
            type="video/mp4"
        />
    </video>
</Story>
