<script lang="ts">
    import type { AnnotationView } from '$lib/api/lightly_studio_local';
    import { getBoundingBox } from '$lib/components/SampleAnnotation/utils';
    import { useRecentClasses } from '$lib/hooks';
    import ClassSearchList from '../ClassSearchList/ClassSearchList.svelte';
    import SourceSearchList from '../SourceSearchList/SourceSearchList.svelte';
    import AnnotationCardCompact from './AnnotationCardCompact.svelte';
    import AnnotationCardFrame from './AnnotationCardFrame.svelte';
    import AnnotationCardHeader from './AnnotationCardHeader.svelte';
    import { recentChips } from './annotationCard.helpers';
    import { useAnnotationCardActions } from './useAnnotationCardActions.svelte';

    interface Props {
        /** The collection that owns the annotation sources. */
        collectionId: string;
        /** The selected box or mask. */
        annotation: AnnotationView;
        refetch: () => void;
        getLayer: () => SVGGraphicsElement | null;
    }

    const { collectionId, annotation, refetch, getLayer }: Props = $props();
    const actions = useAnnotationCardActions(() => ({ collectionId, annotation, refetch }));
    const { recentClasses } = useRecentClasses();

    let view = $state<'compact' | 'search' | 'move'>('compact');
    let searchQuery = $state('');

    const className = $derived(annotation.annotation_label.annotation_label_name);
    const sourceName = $derived(
        actions.sources.data?.find(
            (source) => source.collection_id === annotation.annotation_collection_id
        )?.name ?? 'Annotation source'
    );
    const chips = $derived(recentChips($recentClasses[collectionId] ?? [], className));
    // Stable arrays: the lists reset their first-row highlight when these change identity.
    const classNames = $derived((actions.labels.data ?? []).map((l) => l.annotation_label_name));
    const recent = $derived($recentClasses[collectionId] ?? []);
    const sourceList = $derived(actions.sources.data ?? []);

    const startSearch = (query: string) => {
        searchQuery = query;
        view = 'search';
    };
    const pickClass = (name: string) => {
        view = 'compact';
        void actions.changeClass(name);
    };
    const pickSource = async (name: string) => {
        if (await actions.moveTo(name)) view = 'compact';
    };
</script>

<AnnotationCardFrame bbox={getBoundingBox(annotation)} {getLayer} testId="annotation-card">
    <AnnotationCardHeader
        {sourceName}
        confidence={annotation.confidence}
        title={view === 'move' ? 'Move to…' : undefined}
        onMove={() => (view = 'move')}
        onRemove={actions.remove}
        onClose={actions.close}
    />
    {#if view === 'compact'}
        <AnnotationCardCompact
            {className}
            recentClasses={chips}
            onPickClass={actions.changeClass}
            onSearch={startSearch}
            onRemove={actions.remove}
            onClose={actions.close}
        />
    {:else if view === 'search'}
        <ClassSearchList
            names={classNames}
            {recent}
            initialQuery={searchQuery}
            onPick={pickClass}
            onCancel={() => (view = 'compact')}
        />
    {:else}
        <SourceSearchList
            sources={sourceList}
            excludeSourceId={annotation.annotation_collection_id}
            onPick={pickSource}
            onCancel={() => (view = 'compact')}
        />
    {/if}
</AnnotationCardFrame>
