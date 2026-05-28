<script lang="ts">
    import type { AnnotationCollectionView } from '$lib/api/lightly_studio_local/types.gen';
    import { type BalancingMode } from '$lib/components/Sampling/balancingMode';
    import AnnotationSourceSelect from '$lib/components/AnnotationSourceSelect/AnnotationSourceSelect.svelte';
    import BalancingModeSelect from './BalancingModeSelect.svelte';

    interface Props {
        balancingMode: BalancingMode;
        annotationCollections: AnnotationCollectionView[];
        annotationSourceId: string;
        onBalancingModeChange: (mode: BalancingMode) => void;
        onAnnotationSourceChange: (annotationSourceId: string) => void;
    }

    let {
        balancingMode,
        annotationCollections,
        annotationSourceId,
        onBalancingModeChange,
        onAnnotationSourceChange
    }: Props = $props();

    const sourceOptions = $derived(
        annotationCollections.map((collection) => ({
            id: collection.collection_id,
            name: collection.name
        }))
    );
</script>

<BalancingModeSelect {balancingMode} {onBalancingModeChange} />

<div class="grid grid-cols-4 items-center gap-4">
    <span class="text-right text-foreground">Annotation Source</span>
    <div class="col-span-3">
        <AnnotationSourceSelect
            {sourceOptions}
            selectedSource={annotationSourceId}
            onSelect={onAnnotationSourceChange}
        />
    </div>
</div>
