<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import { fn } from 'storybook/test';
    import MetadataBalancingForm from './MetadataBalancingForm.svelte';

    const { Story } = defineMeta({
        title: 'Components/Sampling/MetadataBalancingForm',
        component: MetadataBalancingForm,
        tags: ['autodocs'],
        argTypes: {
            params: { control: 'object' },
            metadataFieldNames: { control: 'object' },
            metadataValuesByKey: { control: 'object' },
            instanceId: { control: 'text' }
        }
    });

    const metadataFieldNames = ['weather', 'city'];
    const metadataValuesByKey = {
        weather: ['sunny', 'rainy', 'foggy'],
        city: ['zurich', 'berlin']
    };
</script>

<Story
    name="Uniform"
    args={{
        instanceId: 'story',
        params: {
            metadata_key: 'weather',
            target_distribution_mode: 'uniform',
            target_distribution: [],
            strength: 1
        },
        metadataFieldNames,
        metadataValuesByKey,
        onUpdate: fn()
    }}
/>

<Story
    name="NoKeySelected"
    args={{
        instanceId: 'story',
        params: {
            metadata_key: '',
            target_distribution_mode: 'uniform',
            target_distribution: [],
            strength: 1
        },
        metadataFieldNames,
        metadataValuesByKey,
        onUpdate: fn()
    }}
/>

<Story
    name="DictionaryEmpty"
    args={{
        instanceId: 'story',
        params: {
            metadata_key: 'weather',
            target_distribution_mode: 'dictionary',
            target_distribution: [],
            strength: 1
        },
        metadataFieldNames,
        metadataValuesByKey,
        onUpdate: fn()
    }}
/>

<Story
    name="DictionaryWithRows"
    args={{
        instanceId: 'story',
        params: {
            metadata_key: 'weather',
            target_distribution_mode: 'dictionary',
            target_distribution: [
                { class_name: 'sunny', weight: 0.3 },
                { class_name: 'rainy', weight: 0.7 }
            ],
            strength: 1
        },
        metadataFieldNames,
        metadataValuesByKey,
        onUpdate: fn()
    }}
/>
