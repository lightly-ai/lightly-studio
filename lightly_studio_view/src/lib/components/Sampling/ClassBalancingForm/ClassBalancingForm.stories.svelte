<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import { fn } from 'storybook/test';
    import ClassBalancingForm from './ClassBalancingForm.svelte';

    const { Story } = defineMeta({
        title: 'Components/Sampling/ClassBalancingForm',
        component: ClassBalancingForm,
        tags: ['autodocs'],
        argTypes: {
            balancingMode: {
                control: 'select',
                options: ['uniform', 'input', 'dictionary']
            }
        }
    });
</script>

<Story
    name="Default"
    args={{
        collectionId: 'collection-1',
        balancingMode: 'uniform',
        classTargets: {},
        annotationCollections: [],
        annotationSourceId: '',
        onBalancingModeChange: fn(),
        onClassTargetsChange: fn(),
        onAnnotationSourceChange: fn()
    }}
/>
