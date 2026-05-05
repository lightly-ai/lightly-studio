<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import CollectionSearchImage from './CollectionSearchImage.svelte';
    import { fn } from 'storybook/test';

    const { Story } = defineMeta({
        title: 'Components/CollectionSearch/CollectionSearchImage',
        component: CollectionSearchImage,
        tags: ['autodocs']
    });
</script>

<Story
    name="Default"
    args={{
        onClear: fn()
    }}
>
    {#snippet template(args)}
        <CollectionSearchImage {...args} />
    {/snippet}
</Story>

<Story
    name="With Preview"
    args={{
        src: 'https://picsum.photos/150?random=1',
        onClear: fn()
    }}
>
    {#snippet template(args)}
        <CollectionSearchImage {...args} />
    {/snippet}
</Story>
