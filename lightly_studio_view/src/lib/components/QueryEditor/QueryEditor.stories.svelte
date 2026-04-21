<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import QueryEditor from './QueryEditor.svelte';

    const { Story } = defineMeta({
        title: 'Components/QueryEditor',
        component: QueryEditor,
        tags: ['autodocs'],
        argTypes: {
            value: { control: 'text' },
            height: { control: 'text' },
            readOnly: { control: 'boolean' }
        }
    });

    const defaultValue = `# Lightly query examples
ImageSampleField.width > 1920
ImageSampleField.tags.contains("reviewed")
VideoSampleField.duration > 60
`;
</script>

<Story
    name="Default"
    args={{
        value: defaultValue,
        height: '360px'
    }}
/>

<Story
    name="Read only"
    args={{
        value: defaultValue,
        height: '240px',
        readOnly: true
    }}
/>
