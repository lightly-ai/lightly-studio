<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import { fn } from 'storybook/test';
    import SimilarityForm from './SimilarityForm.svelte';

    const { Story } = defineMeta({
        title: 'Components/Sampling/SimilarityForm',
        component: SimilarityForm,
        tags: ['autodocs'],
        argTypes: {
            params: { control: 'object' },
            tags: { control: 'object' }
        }
    });
</script>

<Story
    name="NoTags"
    args={{
        params: { query_tag_id: '', strength: 1 },
        tags: [],
        onUpdate: fn()
    }}
/>

<Story
    name="WithTags"
    args={{
        params: { query_tag_id: '', strength: 1 },
        tags: [
            { tag_id: 'tag-1', name: 'Initial Tag' },
            { tag_id: 'tag-2', name: 'Validation Tag' },
            { tag_id: 'tag-3', name: 'Test Tag' }
        ],
        onUpdate: fn()
    }}
/>

<Story
    name="WithSelectedTag"
    args={{
        params: { query_tag_id: 'tag-2', strength: 1 },
        tags: [
            { tag_id: 'tag-1', name: 'Initial Tag' },
            { tag_id: 'tag-2', name: 'Validation Tag' },
            { tag_id: 'tag-3', name: 'Test Tag' }
        ],
        onUpdate: fn()
    }}
/>
