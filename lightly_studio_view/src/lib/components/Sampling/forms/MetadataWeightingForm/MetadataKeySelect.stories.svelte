<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import { fn } from 'storybook/test';
    import MetadataKeySelect from './MetadataKeySelect.svelte';

    const { Story } = defineMeta({
        title: 'Components/Sampling/MetadataKeySelect',
        component: MetadataKeySelect,
        tags: ['autodocs'],
        argTypes: {
            value: { control: 'text' },
            fieldNames: { control: 'object' }
        }
    });
</script>

<Story
    name="NoSelection"
    args={{
        value: '',
        fieldNames: ['brightness', 'contrast', 'sharpness'],
        onValueChange: fn()
    }}
/>

<Story
    name="WithSelection"
    args={{
        value: 'brightness',
        fieldNames: ['brightness', 'contrast', 'sharpness'],
        onValueChange: fn()
    }}
/>
