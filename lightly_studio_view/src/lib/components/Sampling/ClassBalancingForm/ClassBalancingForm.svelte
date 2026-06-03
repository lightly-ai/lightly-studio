<script lang="ts">
    import { Label } from '$lib/components/ui/label';
    import type { AnnotationCollectionView } from '$lib/api/lightly_studio_local/types.gen';
    import { useAnnotationLabels } from '$lib/hooks/useAnnotationLabels/useAnnotationLabels';
    import type { BalancingMode } from '$lib/components/Sampling/balancingMode';
    import AnnotationSourceSelect from '$lib/components/AnnotationSourceSelect/AnnotationSourceSelect.svelte';
    import BalancingModeSelect from './BalancingModeSelect.svelte';
    import ClassTargetsEditor from './ClassTargetsEditor.svelte';

    interface Props {
        collectionId: string;
        balancingMode: BalancingMode;
        classTargets: Record<string, number>;
        annotationCollections: AnnotationCollectionView[];
        annotationSourceId: string;
        onBalancingModeChange: (mode: BalancingMode) => void;
        onClassTargetsChange: (targets: Record<string, number>) => void;
        onAnnotationSourceChange: (annotationSourceId: string) => void;
    }

    let {
        collectionId,
        balancingMode,
        classTargets,
        annotationCollections,
        annotationSourceId,
        onBalancingModeChange,
        onClassTargetsChange,
        onAnnotationSourceChange
    }: Props = $props();

    const annotationLabelsQuery = useAnnotationLabels(() => ({ collectionId }));
    const annotationLabels = $derived(annotationLabelsQuery.data ?? []);
</script>

<BalancingModeSelect {balancingMode} {onBalancingModeChange} />

{#if balancingMode === 'dictionary'}
    <div class="grid grid-cols-4 items-start gap-4">
        <Label for="class-target" class="pt-2 text-right text-foreground">Class Targets</Label>
        <ClassTargetsEditor {annotationLabels} {classTargets} {onClassTargetsChange} />
    </div>
{/if}

<AnnotationSourceSelect
    sourceOptions={annotationCollections.map((collection) => ({
        id: collection.collection_id,
        name: collection.name
    }))}
    selectedSource={annotationSourceId}
    onSelect={onAnnotationSourceChange}
/>
