import { fromStore } from 'svelte/store';
import { useAnnotationCollections } from '$lib/hooks';
import { useCustomLabelColors } from '$lib/hooks/useCustomLabelColors';
import { getColorByLabel } from '$lib/utils';
import { tickAnnotationsToClasses, tickAnnotationsToCuboids } from '../tickAnnotationsToCuboids';
import type { PointCloudWorkspaceContext } from '../provider/types';
import type { WorkspaceOptions } from '../workspaceOptions';

/** Keeps cloud snapshots, tick metadata, and annotation metadata in the same coordinate frame. */
export function useWorkspaceSceneData(
    getWorkspace: () => PointCloudWorkspaceContext,
    getOptions: () => WorkspaceOptions
) {
    const { customLabelColorsStore } = useCustomLabelColors();
    const annotationCollectionsQuery = useAnnotationCollections(() => ({
        collectionId: getOptions().annotationSourceCollectionId
    }));
    const annotationSources = $derived(
        (annotationCollectionsQuery.data ?? []).map(({ collection_id, name }) => ({
            id: collection_id,
            name
        }))
    );

    const colors = fromStore(customLabelColorsStore);
    // Synchronized snapshot: the cloud frame and its corresponding annotations
    // advance together.
    // The fit key is captured with the snapshot, so the camera is re-centered once the points of
    // the newly selected display frame have loaded, not while the previous frame is still shown.
    let sceneSnapshot = $state<{
        frame: NonNullable<PointCloudWorkspaceContext['cloudPointFrame']['data']>;
        annotations: Parameters<typeof tickAnnotationsToCuboids>[0];
        fitKey: string;
        tick: number;
    } | null>(null);

    $effect(() => {
        const workspace = getWorkspace();
        if (
            workspace.cloudPointFrame.data &&
            !workspace.cloudPointFrame.isPlaceholderData &&
            !workspace.tickDetails.isPlaceholderData
        ) {
            sceneSnapshot = {
                frame: workspace.cloudPointFrame.data,
                annotations: getWorkspace().tickDetails.data?.annotations ?? [],
                fitKey: `${getOptions().sequenceId}/${getWorkspace().referenceFrameId}/${getWorkspace().isShowingSensorFrames}`,
                tick: getWorkspace().currentTick
            };
        }
    });

    // Annotations belong to a specific tick. While the new tick's data is loading (both queries
    // show placeholder data from the previous tick), we keep the previous point cloud visible for
    // a smooth transition but immediately clear the annotations so they don't bleed into frames
    // where they do not belong.
    const currentSnapshot = $derived(
        sceneSnapshot?.tick === getWorkspace().currentTick ? sceneSnapshot : undefined
    );
    const snapshotAnnotations = $derived(currentSnapshot?.annotations ?? []);

    const cuboids = $derived(tickAnnotationsToCuboids(snapshotAnnotations));

    const annotationClasses = $derived.by(() => {
        void colors.current;
        return tickAnnotationsToClasses(
            sceneSnapshot?.annotations ?? [],
            (name) => getColorByLabel(name, 1).color
        );
    });

    // Skip cuboids whose coordinate frame differs from the loaded point cloud.
    // When the cloud falls back to sensor frames (no TF transform available),
    // cuboids requested in the reference frame are filtered out rather than
    // rendered at wrong coordinates.
    const sceneCuboids = $derived.by(() => {
        const frameIds = new Set(sceneSnapshot?.frame.channels.map((c) => c.frameId));
        return cuboids.filter((c) => frameIds.has(c.frameId));
    });

    const tick = $derived.by(() => {
        const details = getWorkspace().tickDetails.data;
        return details
            ? {
                  sampleId: details.sample_id,
                  collectionId: details.collection_id,
                  tags: details.tags,
                  // Placeholder data belongs to the previous tick, so it must not be edited.
                  isStale: getWorkspace().tickDetails.isPlaceholderData
              }
            : undefined;
    });

    return {
        get snapshot() {
            return sceneSnapshot;
        },
        get currentSnapshot() {
            return currentSnapshot;
        },
        get snapshotAnnotations() {
            return snapshotAnnotations;
        },
        get cuboids() {
            return sceneCuboids;
        },
        get annotationClasses() {
            return annotationClasses;
        },
        get annotationSources() {
            return annotationSources;
        },
        get tick() {
            return tick;
        }
    };
}
