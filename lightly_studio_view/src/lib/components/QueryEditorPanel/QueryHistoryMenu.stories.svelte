<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import { fn } from 'storybook/test';
    import QueryHistoryMenu from './QueryHistoryMenu.svelte';

    const { Story } = defineMeta({
        title: 'Components/QueryHistoryMenu',
        component: QueryHistoryMenu,
        tags: ['autodocs']
    });
</script>

<Story
    name="With queries"
    args={{
        queries: [
            'width > 500 AND "reviewed" IN tags',
            'metadata["quality_score"] >= 0.8',
            'height < 200'
        ],
        onSelect: fn()
    }}
/>

<Story name="Empty" args={{ queries: [], onSelect: fn() }} />
