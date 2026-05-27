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
            annotationLabels: { control: 'object' }
        }
    });
</script>

<Story
    name="Uniform"
    args={{
        params: { annotation_source: 'uniform', target_distribution: [], strength: 1 },
        annotationLabels: ['cat', 'dog', 'bird'],
        onUpdate: fn()
    }}
/>

<Story
    name="Input"
    args={{
        params: { annotation_source: 'input', target_distribution: [], strength: 1 },
        annotationLabels: ['cat', 'dog', 'bird'],
        onUpdate: fn()
    }}
/>

<Story
    name="DictionaryEmpty"
    args={{
        params: { annotation_source: 'dictionary', target_distribution: [], strength: 1 },
        annotationLabels: ['cat', 'dog', 'bird'],
        onUpdate: fn()
    }}
/>

<Story
    name="DictionaryWithRows"
    args={{
        params: {
            annotation_source: 'dictionary',
            target_distribution: [
                { class_name: 'cat', weight: 0.2 },
                { class_name: 'dog', weight: 0.8 }
            ],
            strength: 1
        },
        annotationLabels: ['cat', 'dog', 'bird'],
        onUpdate: fn()
    }}
/>
