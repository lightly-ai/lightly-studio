<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import { fn } from 'storybook/test';
    import StrengthField from './StrengthField.svelte';

    const { Story } = defineMeta({
        title: 'Components/Sampling/StrengthField',
        component: StrengthField,
        tags: ['autodocs'],
        argTypes: {
            strength: { control: 'number' }
        }
    });
</script>

<Story
    name="Default"
    args={{
        strength: 1,
        id: 'strength-default',
        testid: 'strength-field-default',
        onUpdate: fn()
    }}
/>

<Story
    name="HighStrength"
    args={{
        strength: 5,
        id: 'strength-high',
        testid: 'strength-field-high',
        onUpdate: fn()
    }}
/>
