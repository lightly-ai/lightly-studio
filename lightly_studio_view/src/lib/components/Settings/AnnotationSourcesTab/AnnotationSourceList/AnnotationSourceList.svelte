<script lang="ts">
    import type { SampleType } from '$lib/api/lightly_studio_local';
    import { AnnotationSourceRow } from '../AnnotationSourceRow';
    import { getSourceOwnerLabel } from './getSourceOwnerLabel';

    interface AnnotationSourceItem {
        collection_id: string;
        name: string;
        annotation_count: number;
        parent_collection_id: string;
        parent_sample_type: SampleType;
        parent_group_component_name?: string | null;
    }

    interface Props {
        sources: AnnotationSourceItem[];
        isLoading: boolean;
        isError: boolean;
        onDelete: (source: AnnotationSourceItem) => void;
    }

    const { sources, isLoading, isError, onDelete }: Props = $props();
    // Name where each source lives only when the sources live in more than one place, for
    // example under the videos and under the frames of a video dataset.
    const showOwner = $derived(new Set(sources.map((s) => s.parent_collection_id)).size > 1);
</script>

<ul class="mx-auto flex max-w-lg flex-col">
    {#if isLoading}
        <li class="px-2 py-3 text-sm text-muted-foreground">Loading annotation sources…</li>
    {:else if isError}
        <li class="px-2 py-3 text-sm text-muted-foreground">
            Could not load the annotation sources.
        </li>
    {/if}
    {#each sources as source (source.collection_id)}
        <AnnotationSourceRow
            name={source.name}
            owner={showOwner ? getSourceOwnerLabel(source) : undefined}
            annotationCount={source.annotation_count}
            onDelete={() => onDelete(source)}
        />
    {/each}
</ul>
