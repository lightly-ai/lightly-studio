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
</script>

<Story
    name="Default"
    args={{
        height: '360px'
    }}
/>

<Story
    name="Read only"
    args={{
        height: '240px',
        readOnly: true
    }}
/>
