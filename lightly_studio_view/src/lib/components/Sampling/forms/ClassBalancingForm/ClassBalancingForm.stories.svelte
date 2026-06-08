<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import { fn } from 'storybook/test';
    import ClassBalancingForm from './ClassBalancingForm.svelte';

    const { Story } = defineMeta({
        title: 'Components/Sampling/ClassBalancingForm',
        component: ClassBalancingForm,
        tags: ['autodocs'],
        argTypes: {
            params: { control: 'object' },
            annotationLabels: { control: 'object' },
            annotationSourceOptions: { control: 'object' },
            instanceId: { control: 'text' }
        }
    });
</script>

<Story
    name="Uniform"
    args={{
        params: {
            annotation_source_id: '',
            target_distribution_mode: 'uniform',
            target_distribution: [],
            strength: 1
        },
        instanceId: 'story',
        annotationLabels: ['cat', 'dog', 'bird'],
        annotationSourceOptions: [
            { id: 'source-1', name: 'Ground Truth' },
            { id: 'source-2', name: 'Predictions v1' }
        ],
        onUpdate: fn()
    }}
/>

<Story
    name="Input"
    args={{
        params: {
            annotation_source_id: '',
            target_distribution_mode: 'input',
            target_distribution: [],
            strength: 1
        },
        instanceId: 'story',
        annotationLabels: ['cat', 'dog', 'bird'],
        annotationSourceOptions: [
            { id: 'source-1', name: 'Ground Truth' },
            { id: 'source-2', name: 'Predictions v1' }
        ],
        onUpdate: fn()
    }}
/>

<Story
    name="DictionaryEmpty"
    args={{
        params: {
            annotation_source_id: '',
            target_distribution_mode: 'dictionary',
            target_distribution: [],
            strength: 1
        },
        instanceId: 'story',
        annotationLabels: ['cat', 'dog', 'bird'],
        annotationSourceOptions: [
            { id: 'source-1', name: 'Ground Truth' },
            { id: 'source-2', name: 'Predictions v1' }
        ],
        onUpdate: fn()
    }}
/>

<Story
    name="DictionaryWithRows"
    args={{
        params: {
            annotation_source_id: '',
            target_distribution_mode: 'dictionary',
            target_distribution: [
                { class_name: 'cat', weight: 0.2 },
                { class_name: 'dog', weight: 0.8 }
            ],
            strength: 1
        },
        instanceId: 'story',
        annotationLabels: ['cat', 'dog', 'bird'],
        annotationSourceOptions: [
            { id: 'source-1', name: 'Ground Truth' },
            { id: 'source-2', name: 'Predictions v1' }
        ],
        onUpdate: fn()
    }}
/>
