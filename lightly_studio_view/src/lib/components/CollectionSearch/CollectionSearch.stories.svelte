<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import CollectionSearch from './CollectionSearch.svelte';

    const { Story } = defineMeta({
        title: 'Components/CollectionSearch',
        component: CollectionSearch,
        tags: ['autodocs']
    });

    const noopSetTextEmbedding = () => undefined;
</script>

<Story
    name="Default"
    args={{
        collectionId: 'collection-id',
        textEmbedding: undefined,
        setTextEmbedding: noopSetTextEmbedding
    }}
    asChild
>
    {#snippet children(args)}
        <div class="w-[480px]">
            <CollectionSearch {...args} />
        </div>
    {/snippet}
</Story>

<Story
    name="With Existing Query"
    args={{
        collectionId: 'collection-id',
        textEmbedding: {
            queryText: 'a yellow excavator',
            embedding: [0, 0, 0]
        },
        setTextEmbedding: noopSetTextEmbedding
    }}
    asChild
>
    {#snippet children(args)}
        <div class="w-[480px]">
            <CollectionSearch {...args} />
        </div>
    {/snippet}
</Story>
