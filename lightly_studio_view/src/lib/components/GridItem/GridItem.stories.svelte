<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import GridItem from './GridItem.svelte';

    const { Story } = defineMeta({
        title: 'Components/GridItem',
        component: GridItem,
        tags: ['autodocs'],
        argTypes: {
            width: { control: 'number' },
            height: { control: 'number' }
        }
    });
</script>

<Story name="With Image">
    <img src="https://picsum.photos/300" alt="Placeholder" class="h-full w-full object-cover" />
</Story>

<Story name="With Video">
    <video autoplay muted loop class="h-full w-full object-cover">
        <source
            src="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
            type="video/mp4"
        />
    </video>
</Story>
