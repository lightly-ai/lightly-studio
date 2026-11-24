<script lang="ts">
    import { Segment } from '$lib/components';
    import TagsIcon from '@lucide/svelte/icons/tags';
    import { TagsEditor } from './TagsEditor';
    import type { TagItem } from './types';

    interface Props {
        tags: TagItem[];
        collectionId: string;
        sampleId: string;
        onRefetch?: () => void;
        title?: string;
    }

    let { tags, collectionId, sampleId, onRefetch, title = 'Tags' }: Props = $props();
</script>

<Segment {title} icon={TagsIcon}>
    <TagsEditor {tags} {collectionId} {sampleId} {onRefetch} />
</Segment>
