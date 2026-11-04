<script lang="ts">
    import { Trash2, X } from '@lucide/svelte';
    import type { AnnotationView } from '$lib/api/lightly_studio_local';
    import { getBoundingBox } from '$lib/components/SampleAnnotation/utils';
    import { useRecentClasses } from '$lib/hooks';
    import { getColorByLabel } from '$lib/utils';
    import AnnotationCardCompact from './AnnotationCardCompact.svelte';
    import AnnotationCardFrame from './AnnotationCardFrame.svelte';
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

    const className = $derived(annotation.annotation_label.annotation_label_name);
    const sourceName = $derived(
        actions.sources.data?.find(
            (source) => source.collection_id === annotation.annotation_collection_id
        )?.name ?? 'Annotation source'
    );
    const chips = $derived(recentChips($recentClasses[collectionId] ?? [], className));
    const iconButtonClass =
        'inline-flex size-6 items-center justify-center rounded-md text-muted-foreground hover:text-foreground';

    const startSearch = () => {
        view = 'search';
    };
</script>

<AnnotationCardFrame bbox={getBoundingBox(annotation)} {getLayer} testId="annotation-card">
    <div class="flex items-center gap-1">
        <button
            type="button"
            class="inline-flex min-w-0 items-center gap-1.5 rounded-md border px-2 py-0.5 text-xs hover:bg-accent"
            title="Move to another annotation source"
        >
            <span
                class="size-2 shrink-0 rounded-full"
                style:background-color={getColorByLabel(sourceName, 1).color}
            ></span>
            <span class="truncate">{sourceName}</span>
        </button>
        {#if annotation.confidence != null}
            <span class="text-xs text-muted-foreground">{annotation.confidence.toFixed(2)}</span>
        {/if}
        <span class="flex-1"></span>
        <button
            type="button"
            class={iconButtonClass}
            aria-label="Delete annotation"
            title="Delete annotation (Del)"
            onclick={actions.remove}
        >
            <Trash2 class="size-4" />
        </button>
        <button
            type="button"
            class={iconButtonClass}
            aria-label="Close"
            title="Close (Esc)"
            onclick={actions.close}
        >
            <X class="size-4" />
        </button>
    </div>
    {#if view === 'compact'}
        <AnnotationCardCompact
            {className}
            recentClasses={chips}
            onPickClass={actions.changeClass}
            onSearch={startSearch}
            onRemove={actions.remove}
            onClose={actions.close}
        />
    {/if}
</AnnotationCardFrame>
