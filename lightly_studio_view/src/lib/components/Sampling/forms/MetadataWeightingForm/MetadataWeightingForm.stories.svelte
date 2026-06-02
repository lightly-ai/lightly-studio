<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import { fn } from 'storybook/test';
    import MetadataWeightingForm from './MetadataWeightingForm.svelte';

    const { Story } = defineMeta({
        title: 'Components/Sampling/MetadataWeightingForm',
        component: MetadataWeightingForm,
        tags: ['autodocs'],
        argTypes: {
            params: { control: 'object' },
            metadataFieldNames: { control: 'object' }
        }
    });
</script>

<Story
    name="WithNoMetadataFieldKey"
    args={{
        params: { metadata_key: null, strength: 1 },
        metadataFieldNames: ['brightness', 'contrast', 'sharpness'],
        onUpdate: fn()
    }}
/>

<Story
    name="WithMetadataFields"
    args={{
        params: { metadata_key: 'brightness', strength: 1 },
        metadataFieldNames: ['brightness', 'contrast', 'sharpness'],
        onUpdate: fn()
    }}
/>
