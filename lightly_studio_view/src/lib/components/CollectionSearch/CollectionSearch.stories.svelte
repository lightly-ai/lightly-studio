<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import { fn } from 'storybook/test';
    import CollectionSearch from './CollectionSearch.svelte';

    const { Story } = defineMeta({
        title: 'Components/CollectionSearch',
        component: CollectionSearch,
        tags: ['autodocs']
    });
</script>

<Story
    name="Default"
    args={{
        image: undefined,
        onSubmitText: fn(),
        onSubmitFile: fn(),
        onClear: fn(),
        onError: fn()
    }}
>
    {#snippet template(args)}
        <CollectionSearch {...args} />
    {/snippet}
</Story>

<Story
    name="With Existing Query"
    args={{
        image: undefined,
        initialQueryText: 'a yellow excavator',
        onSubmitText: fn(),
        onSubmitFile: fn(),
        onClear: fn(),
        onError: fn()
    }}
>
    {#snippet template(args)}
        <CollectionSearch {...args} />
    {/snippet}
</Story>

<Story
    name="With Image"
    args={{
        image: {
            name: 'excavator.png',
            previewUrl: 'https://placehold.co/64x64'
        },
        onSubmitText: fn(),
        onSubmitFile: fn(),
        onClear: fn(),
        onError: fn()
    }}
>
    {#snippet template(args)}
        <CollectionSearch {...args} />
    {/snippet}
</Story>

<Story
    name="Pending"
    args={{
        image: undefined,
        isPending: true,
        initialQueryText: 'a yellow excavator',
        onSubmitText: fn(),
        onSubmitFile: fn(),
        onClear: fn(),
        onError: fn()
    }}
>
    {#snippet template(args)}
        <CollectionSearch {...args} />
    {/snippet}
</Story>
