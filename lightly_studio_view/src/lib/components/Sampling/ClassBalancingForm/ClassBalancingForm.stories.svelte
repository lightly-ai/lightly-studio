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
                options: ['uniform', 'input']
            }
        }
    });
</script>

<Story
    name="Default"
    args={{
        balancingMode: 'uniform',
        onBalancingModeChange: fn()
    }}
/>
