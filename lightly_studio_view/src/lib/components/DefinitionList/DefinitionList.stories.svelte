<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import DefinitionList from './DefinitionList.svelte';

    const { Story } = defineMeta({
        title: 'Components/DefinitionList',
        component: DefinitionList,
        tags: ['autodocs'],
        argTypes: {
            items: { control: 'object' }
        }
    });
</script>

<Story
    name="Default"
    args={{
        items: [
            { label: 'Name:', value: 'John Doe' },
            { label: 'Email:', value: 'john@example.com' },
            { label: 'Phone:', value: '+1 234 567 8900' }
        ]
    }}
/>

<Story
    name="Video Details"
    args={{
        items: [
            { label: 'File Name:', value: 'sample_video.mp4', testId: 'video-file-name' },
            { label: 'Width:', value: '1920px', testId: 'video-width' },
            { label: 'Height:', value: '1080px', testId: 'video-height' },
            { label: 'Duration:', value: '12.50 seconds' },
            { label: 'FPS:', value: '30.00' }
        ]
    }}
/>

<Story
    name="Image Metadata"
    args={{
        items: [
            { label: 'Height:', value: '1080px', testId: 'sample-metadata-height' },
            { label: 'Width:', value: '1920px', testId: 'sample-metadata-width' },
            { label: 'Filename:', value: 'image_001.jpg', testId: 'sample-metadata-filename' },
            {
                label: 'Filepath:',
                value: '/datasets/my_dataset/images/image_001.jpg',
                testId: 'sample-metadata-filepath'
            }
        ]
    }}
/>

<Story
    name="With Null Values"
    args={{
        items: [
            { label: 'Name:', value: 'Test Sample' },
            { label: 'Description:', value: null },
            { label: 'Category:', value: undefined },
            { label: 'Status:', value: 'Active' }
        ]
    }}
/>

<Story
    name="Empty List"
    args={{
        items: []
    }}
/>

<Story
    name="Mixed Data Types"
    args={{
        items: [
            { label: 'Count:', value: 42 },
            { label: 'Percentage:', value: 87.5 },
            { label: 'Name:', value: 'Sample Name' },
            { label: 'Active:', value: 'true' }
        ]
    }}
/>
