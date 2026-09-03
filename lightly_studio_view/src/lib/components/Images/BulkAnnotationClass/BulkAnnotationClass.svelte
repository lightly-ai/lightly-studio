<script lang="ts">
    import { toast } from 'svelte-sonner';
    import { get } from 'svelte/store';
    import { Card, CardContent } from '$lib/components';
    import BulkAnnotationClassPanel from '$lib/components/BulkAnnotationClassPanel/BulkAnnotationClassPanel.svelte';
    import { useAnnotationCollections } from '$lib/hooks/useAnnotationCollections/useAnnotationCollections';
    import { useAnnotationLabels } from '$lib/hooks/useAnnotationLabels/useAnnotationLabels';
    import { useBulkAddAnnotationClass } from '$lib/hooks/useBulkAddAnnotationClass/useBulkAddAnnotationClass';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import {
        formatApplyResult,
        resolveAnnotationSource,
        toAnnotationClassOptions
    } from './BulkAnnotationClass.helpers';

    interface Props {
        collectionId: string;
    }

    const { collectionId }: Props = $props();

    const {
        getSelectedSampleIds,
        isEditingMode,
        lastAnnotationSource,
        updateLastAnnotationSource
    } = useGlobalStorage();

    const selectedSampleIds = $derived(getSelectedSampleIds(collectionId));
    const selectedCount = $derived($selectedSampleIds.size);
    const isVisible = $derived($isEditingMode && selectedCount > 0);

    const annotationCollections = useAnnotationCollections(() => ({ collectionId }));
    const annotationLabels = useAnnotationLabels(() => ({ collectionId }));

    const sourceNames = $derived(annotationCollections.data?.map((source) => source.name) ?? []);
    const selectedSource = $derived(
        resolveAnnotationSource({ lastSource: $lastAnnotationSource[collectionId], sourceNames })
    );

    const { addAnnotationClass } = useBulkAddAnnotationClass({
        getCollectionId: () => collectionId
    });

    let isApplying = $state(false);

    const handleApply = async ({ className, source }: { className: string; source: string }) => {
        if (isApplying) return;
        isApplying = true;
        try {
            const result = await addAnnotationClass({
                className,
                annotationSource: source,
                selectedSampleIds: get(getSelectedSampleIds(collectionId))
            });
            toast.success(
                formatApplyResult({
                    createdCount: result.created_count,
                    skippedCount: result.skipped_count
                })
            );
        } catch {
            toast.error('Failed to add the class. Please try again.');
        } finally {
            isApplying = false;
        }
    };
</script>

<!--
    Sits beside the grid, mirroring the annotation grid's SelectedAnnotations panel, so it never
    occludes the tiles the user is checking their work against.
-->
{#if isVisible}
    <div class="min-w-[250px] max-w-[30%] flex-1">
        <Card className="h-full">
            <CardContent className="h-full flex flex-col">
                <div
                    class="flex h-full min-h-0 flex-col space-y-4 overflow-hidden dark:[color-scheme:dark]"
                >
                    <BulkAnnotationClassPanel
                        {selectedCount}
                        annotationClasses={toAnnotationClassOptions(annotationLabels.data)}
                        annotationSources={sourceNames}
                        {selectedSource}
                        {isApplying}
                        onSourceChange={(source) =>
                            updateLastAnnotationSource(collectionId, source)}
                        onApply={handleApply}
                    />
                </div>
            </CardContent>
        </Card>
    </div>
{/if}
