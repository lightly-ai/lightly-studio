<script lang="ts">
    import type { AnnotationView } from '$lib/api/lightly_studio_local';
    import {
        ClassSearchList,
        SourceSearchList,
        recentChips,
        useClassSearchData
    } from '$lib/components/SampleDetails/SearchList';
    import { AnnotationCardCompact } from './AnnotationCardCompact';
    import { AnnotationCardFrame } from './AnnotationCardFrame';
    import { AnnotationCardHeader } from './AnnotationCardHeader';
    import { useAnnotationCardActions } from './useAnnotationCardActions.svelte';
    import { useCardBox } from './useCardBox.svelte';
    import { useCardView } from './useCardView.svelte';

    interface Props {
        /** The collection that owns the annotation sources. */
        collectionId: string;
        /** The selected box or mask. */
        annotation: AnnotationView;
        refetch: () => void;
        getLayer: () => SVGGraphicsElement | null;
        /** Whether boxes are colored by source, so the card marks the source, not the class. */
        colorBySource: boolean;
    }

    const { collectionId, annotation, refetch, getLayer, colorBySource }: Props = $props();
    // Whether the card is shown, so its keys act. The frame sets it.
    let isActive = $state(false);
    const actions = useAnnotationCardActions(() => ({ collectionId, annotation, refetch }));
    const classSearch = useClassSearchData(() => collectionId);
    const cardBox = useCardBox(() => annotation);
    const view = useCardView(() => isActive);

    const className = $derived(annotation.annotation_label.annotation_label_name);
    // A stable array: the list resets its first-row highlight when it changes identity.
    const sourceList = $derived(actions.sources.data ?? []);

    const pickClass = (name: string) => {
        view.show('compact');
        void actions.changeClass(name);
    };
    const pickSource = async (name: string) => {
        if (await actions.moveTo(name)) view.show('compact');
    };
</script>

<svelte:window onkeydowncapture={view.handleWindowKeydown} />

<AnnotationCardFrame
    bbox={cardBox.current}
    {getLayer}
    label="Annotation {className}"
    testId="annotation-card"
    bind:isActive
>
    <AnnotationCardHeader
        sources={sourceList}
        sourceId={annotation.annotation_collection_id}
        confidence={annotation.confidence}
        showSourceColor={colorBySource}
        title={view.current === 'move' ? 'Move to…' : undefined}
        onMove={() => view.show('move')}
        onRemove={actions.remove}
        onClose={actions.close}
    />
    {#if view.current === 'compact'}
        <AnnotationCardCompact
            {className}
            showClassColor={!colorBySource}
            {isActive}
            recentClasses={recentChips(classSearch.recent, className)}
            onPickClass={actions.changeClass}
            onSearch={() => view.show('search')}
            onRemove={actions.remove}
            onClose={actions.close}
        />
    {:else if view.current === 'search'}
        <ClassSearchList
            names={classSearch.classNames}
            recent={classSearch.recent}
            current={className}
            showBackHint
            onPick={pickClass}
            onCancel={() => view.show('compact')}
        />
    {:else}
        <SourceSearchList
            {collectionId}
            excludeSourceId={annotation.annotation_collection_id}
            disabled={actions.isMoving}
            showBackHint
            onPick={pickSource}
            onCancel={() => view.show('compact')}
        />
    {/if}
</AnnotationCardFrame>
