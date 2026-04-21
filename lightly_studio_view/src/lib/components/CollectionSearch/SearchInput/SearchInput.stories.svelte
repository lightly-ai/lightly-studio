<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import SearchInput from './SearchInput.svelte';

    const { Story } = defineMeta({
        title: 'Components/CollectionSearch/SearchInput',
        component: SearchInput,
        tags: ['autodocs']
    });
</script>

<Story
    name="Default"
    args={{
        queryText: '',
        submittedQueryText: '',
        isUploading: false,
        dragOver: false,
        onKeyDown: () => undefined,
        onPaste: () => undefined,
        onClear: () => undefined,
        onUploadClick: () => undefined,
        onQueryTextChange: () => undefined
    }}
    asChild
>
    {#snippet children(args)}
        <SearchInput {...args} />
    {/snippet}
</Story>

<Story
    name="With Query"
    args={{
        queryText: 'a red sports car',
        submittedQueryText: 'a red sports car',
        isUploading: false,
        dragOver: false,
        onKeyDown: () => undefined,
        onPaste: () => undefined,
        onClear: () => undefined,
        onUploadClick: () => undefined,
        onQueryTextChange: () => undefined
    }}
    asChild
>
    {#snippet children(args)}
        <SearchInput {...args} />
    {/snippet}
</Story>
