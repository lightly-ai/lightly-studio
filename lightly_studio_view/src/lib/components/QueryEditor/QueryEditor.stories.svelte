<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import QueryEditor from './QueryEditor.svelte';
    import { fn } from 'storybook/test';

    const { Story } = defineMeta({
        title: 'Components/QueryEditor',
        component: QueryEditor,
        tags: ['autodocs'],
        argTypes: {
            value: { control: 'text' },
            height: { control: 'text' },
            readOnly: { control: 'boolean' },
            onSave: { action: 'save' }
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

<Story
    name="With save"
    args={{
        height: '320px',
        onSave: fn()
    }}
/>
