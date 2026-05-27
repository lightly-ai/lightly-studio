<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import { fn } from 'storybook/test';
    import StrategySelect from './StrategySelect.svelte';

    const { Story } = defineMeta({
        title: 'Components/Selection/StrategySelect',
        component: StrategySelect,
        tags: ['autodocs'],
        argTypes: {
            value: {
                control: 'select',
                options: ['', 'diversity', 'typicality', 'similarity', 'class_balancing']
            },
            isSimilaritySupported: { control: 'boolean' }
        }
    });
</script>

<Story
    name="Default"
    args={{
        value: '',
        isSimilaritySupported: true,
        onValueChange: fn()
    }}
/>

<Story
    name="Selected"
    args={{
        value: 'diversity',
        isSimilaritySupported: true,
        onValueChange: fn()
    }}
/>

<Story
    name="SimilarityDisabled"
    args={{
        value: '',
        isSimilaritySupported: false,
        onValueChange: fn()
    }}
/>
