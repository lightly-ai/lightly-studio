<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import { fn } from 'storybook/test';
    import DeduplicationForm from './DeduplicationForm.svelte';

    const { Story } = defineMeta({
        title: 'Components/Sampling/DeduplicationForm',
        component: DeduplicationForm,
        tags: ['autodocs'],
        argTypes: {
            params: { control: 'object' }
        }
    });
</script>

<Story
    name="Default"
    args={{
        params: { strength: 1, stopping_condition_minimum_distance: 0.1 },
        onUpdate: fn()
    }}
/>
