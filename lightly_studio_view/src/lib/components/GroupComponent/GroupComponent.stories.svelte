<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import GroupComponent from './GroupComponent.svelte';

    const { Story } = defineMeta({
        title: 'Components/GroupComponent',
        component: GroupComponent,
        tags: ['autodocs'],
        argTypes: {
            src: { control: 'text' },
            title: { control: 'text' },
            type: { control: 'select', options: ['image', 'video'] }
        }
    });
</script>

<Story
    name="Image"
    args={{
        src: 'https://picsum.photos/300/300',
        title: 'Component 1',
        type: 'image'
    }}
/>

<Story
    name="Video"
    args={{
        src: 'https://www.w3schools.com/html/mov_bbb.mp4',
        title: 'Video 1',
        type: 'video'
    }}
/>
