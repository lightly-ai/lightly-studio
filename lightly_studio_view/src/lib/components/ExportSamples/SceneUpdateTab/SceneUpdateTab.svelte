<script lang="ts">
    import { createQuery } from '@tanstack/svelte-query';
    import { FormField, Select, AnnotationSourceSelect } from '$lib/components';
    import * as Tabs from '$lib/components/ui/tabs/index.js';
    import {
        exportCollectionSceneUpdatePrepare,
        type exportCollectionSceneUpdateOptions
    } from '$lib/api/lightly_studio_local';
    import { exportCollectionSceneUpdateOptionsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
    import { PUBLIC_LIGHTLY_STUDIO_API_URL } from '$env/static/public';
    import { useExportDownload, triggerDownload } from '../useExportDownload';
    import ExportDownloadButton from '../ExportDownloadButton/ExportDownloadButton.svelte';
    import SceneUpdateFileFields from './SceneUpdateFileFields/SceneUpdateFileFields.svelte';
    import SceneUpdateS3Write from './SceneUpdateS3Write/SceneUpdateS3Write.svelte';
    import { isValidSuffix } from './sceneUpdateFileOptions';

    interface Props {
        /** The ID of the collection the export runs on. */
        collectionId: string;
        /** The recordings to export: one sequence or an MCAP sequence filter. */
        scope: Parameters<typeof exportCollectionSceneUpdateOptions>[0]['body'];
        /** Optional callback invoked when the download button is clicked. */
        onDownloadClick?: () => void;
    }

    let { collectionId, scope, onDownloadClick }: Props = $props();

    const optionsQuery = createQuery(() =>
        exportCollectionSceneUpdateOptionsOptions({
            path: { collection_id: collectionId },
            body: scope
        })
    );

    let selectedSourceId = $state<string>();
    let selectedFrameId = $state<string>();
    let topicInput = $state<string>();
    let suffixInput = $state<string>();

    const annotationCollections = $derived(optionsQuery.data?.annotation_collections ?? []);
    const sources = $derived(
        annotationCollections.map((c) => ({
            id: c.collection_id,
            name: c.name
        }))
    );
    const sourceId = $derived(
        selectedSourceId && sources.some((s) => s.id === selectedSourceId)
            ? selectedSourceId
            : (sources.find((s) => s.name === 'ground_truth') ?? sources[0])?.id
    );
    // Each source lists the frames its cuboids can be exported in.
    const frameIds = $derived(
        annotationCollections.find((c) => c.collection_id === sourceId)?.frame_ids ?? []
    );
    const frameId = $derived(
        selectedFrameId && frameIds.includes(selectedFrameId) ? selectedFrameId : frameIds[0]
    );
    // The options give the defaults until the user edits a field.
    const topic = $derived(topicInput ?? optionsQuery.data?.topic ?? '');
    const suffix = $derived(suffixInput ?? optionsQuery.data?.suffix ?? '');
    const hasNoSequences = $derived(optionsQuery.data?.sequence_count === 0);
    const hasNoSharedFrame = $derived(!!sourceId && frameIds.length === 0);
    const canExport = $derived(!!sourceId && !!frameId && !!topic && isValidSuffix(suffix));

    const requestBody = () => ({
        ...scope,
        annotation_collection_id: sourceId!,
        target_frame_id: frameId!,
        topic,
        suffix
    });

    const { isLoading, errorMessage, handleDownload } = useExportDownload(async () => {
        const response = await exportCollectionSceneUpdatePrepare({
            path: { collection_id: collectionId },
            body: requestBody()
        });
        if (response.error) throw new Error(JSON.stringify(response.error));
        const exportKey = response.data?.export_key;
        if (!exportKey) throw new Error('Unexpected empty response data');
        triggerDownload(
            `${PUBLIC_LIGHTLY_STUDIO_API_URL}api/collections/${collectionId}/export/download/${exportKey}`
        );
    });
</script>

<div class="pt-2">
    <p class="text-sm text-muted-foreground">
        Export the cuboid annotations as Foxglove SceneUpdate MCAP files, one per recording.
    </p>

    <div class="mt-6 space-y-4">
        <FormField label="Annotation Source">
            <AnnotationSourceSelect
                sourceOptions={sources}
                selectedSource={sourceId}
                onSelect={(id) => (selectedSourceId = id)}
            />
        </FormField>
        <FormField label="Coordinate Frame">
            <Select
                items={frameIds.map((id) => ({ value: id, label: id }))}
                value={frameId}
                class="w-full"
                disabled={hasNoSharedFrame}
                onValueChange={(id) => (selectedFrameId = id)}
            />
        </FormField>
        {#if optionsQuery.data}
            <SceneUpdateFileFields
                {topic}
                {suffix}
                onTopicChange={(value) => (topicInput = value)}
                onSuffixChange={(value) => (suffixInput = value)}
            />
        {/if}
        {#if hasNoSequences}
            <p class="text-sm text-destructive">No sequences match the current filters.</p>
        {:else if hasNoSharedFrame}
            <p class="text-sm text-destructive">
                The selected recordings share no coordinate frame.
            </p>
        {/if}
    </div>

    <Tabs.Root value="local" class="mt-6">
        <FormField label="Destination">
            <Tabs.List class="grid w-full grid-cols-2">
                <Tabs.Trigger value="local">Local</Tabs.Trigger>
                <Tabs.Trigger value="cloud" data-testid="scene-update-cloud-tab">
                    Cloud (S3)
                </Tabs.Trigger>
            </Tabs.List>
        </FormField>
        <Tabs.Content value="local">
            <ExportDownloadButton
                isLoading={$isLoading}
                disabled={!canExport}
                errorMessage={$errorMessage}
                onclick={() => {
                    onDownloadClick?.();
                    handleDownload();
                }}
                testId="scene-update-download-button"
            />
        </Tabs.Content>
        <Tabs.Content value="cloud">
            <SceneUpdateS3Write {collectionId} {canExport} {requestBody} />
        </Tabs.Content>
    </Tabs.Root>
</div>
