<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import FieldTooltip from './FieldTooltip.svelte';

    const { Story } = defineMeta({
        title: 'Components/FieldTooltip',
        component: FieldTooltip,
        tags: ['autodocs'],
        argTypes: {
            content: { control: 'text' }
        }
    });
</script>

<Story
    name="Default"
    args={{
        content: 'This field controls the threshold value for sampling.'
    }}
/>

<Story
    name="LongContent"
    args={{
        content:
            'A longer description that explains in detail what this field does and why it matters for the configuration.'
    }}
/>
