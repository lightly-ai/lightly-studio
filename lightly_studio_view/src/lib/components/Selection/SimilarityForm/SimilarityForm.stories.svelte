<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import { fn } from 'storybook/test';
    import SimilarityForm from './SimilarityForm.svelte';

    const { Story } = defineMeta({
        title: 'Components/Selection/SimilarityForm',
        component: SimilarityForm,
        tags: ['autodocs']
    });
</script>

<Story
    name="Default"
    args={{
        queryTagId: '',
        tags: [
            { tag_id: 'tag-1', name: 'Validation Set' },
            { tag_id: 'tag-2', name: 'Reference Samples' }
        ],
        onQueryTagChange: fn()
    }}
/>

<Story
    name="WithSelectedTag"
    args={{
        queryTagId: 'tag-1',
        tags: [
            { tag_id: 'tag-1', name: 'Validation Set' },
            { tag_id: 'tag-2', name: 'Reference Samples' }
        ],
        onQueryTagChange: fn()
    }}
/>

<Story
    name="NoTags"
    args={{
        queryTagId: '',
        tags: [],
        onQueryTagChange: fn()
    }}
/>
