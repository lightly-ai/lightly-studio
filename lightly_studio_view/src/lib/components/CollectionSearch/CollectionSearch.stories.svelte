<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import { fn } from 'storybook/test';
    import { QueryClient, QueryClientProvider } from '@tanstack/svelte-query';
    import CollectionSearch from './CollectionSearch.svelte';

    const { Story } = defineMeta({
        title: 'Components/CollectionSearch',
        component: CollectionSearch,
        tags: ['autodocs']
    });

    const queryClient = new QueryClient({
        defaultOptions: {
            queries: { retry: false },
            mutations: { retry: false }
        }
    });
</script>

<Story
    name="Default"
    args={{
        collectionId: 'collection-id',
        value: undefined,
        onChange: fn()
    }}
>
    {#snippet template(args)}
        <QueryClientProvider client={queryClient}>
            <CollectionSearch {...args} />
        </QueryClientProvider>
    {/snippet}
</Story>

<Story
    name="With Existing Query"
    args={{
        collectionId: 'collection-id',
        value: {
            queryText: 'a yellow excavator',
            embedding: [0, 0, 0]
        },
        onChange: fn()
    }}
>
    {#snippet template(args)}
        <QueryClientProvider client={queryClient}>
            <CollectionSearch {...args} />
        </QueryClientProvider>
    {/snippet}
</Story>
