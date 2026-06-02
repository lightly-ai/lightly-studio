<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import { fn } from 'storybook/test';
    import StrategyCard from './StrategyCard.svelte';

    const { Story } = defineMeta({
        title: 'Components/Sampling/StrategyCard',
        component: StrategyCard,
        tags: ['autodocs'],
        args: {
            tags: [
                { tag_id: 'tag-1', name: 'Initial Tag' },
                { tag_id: 'tag-2', name: 'Curated Set' }
            ],
            annotationLabels: ['cat', 'dog', 'bird'],
            onRemove: fn(),
            onDuplicate: fn(),
            onUpdate: fn(),
            onToggleExpand: fn()
        }
    });
</script>

<Story
    name="Diversity"
    args={{
        instance: {
            id: 'story-1',
            type: 'diversity',
            params: { strength: 1 },
            isExpanded: true
        }
    }}
/>

<Story
    name="Typicality"
    args={{
        instance: {
            id: 'story-2',
            type: 'typicality',
            params: { strength: 1 },
            isExpanded: true
        }
    }}
/>

<Story
    name="Similarity"
    args={{
        instance: {
            id: 'story-3',
            type: 'similarity',
            params: { query_tag_id: 'tag-1', strength: 1 },
            isExpanded: true
        }
    }}
/>

<Story
    name="MetadataWeighting"
    args={{
        instance: {
            id: 'story-4',
            type: 'metadata_weighting',
            params: { metadata_key: 'sharpness', strength: 1 },
            isExpanded: true
        }
    }}
/>

<Story
    name="ClassBalancing"
    args={{
        instance: {
            id: 'story-5',
            type: 'class_balancing',
            params: {
                annotation_source: 'dictionary',
                target_distribution: [
                    { class_name: 'cat', weight: 2 },
                    { class_name: 'dog', weight: 1 }
                ],
                strength: 1
            },
            isExpanded: true
        }
    }}
/>

<Story
    name="Collapsed"
    args={{
        instance: {
            id: 'story-6',
            type: 'diversity',
            params: { strength: 1 },
            isExpanded: false
        }
    }}
/>
