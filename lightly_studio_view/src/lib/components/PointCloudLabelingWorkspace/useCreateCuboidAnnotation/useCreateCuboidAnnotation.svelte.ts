import {
    AnnotationClassNotAvailableError,
    getCreateLabelErrorMessage,
    useAnnotationLabels,
    useCreateAnnotation,
    useCreateLabel,
    useGlobalStorage,
    useSelectClassDialog,
    useTracks
} from '$lib/hooks';
import { get } from 'svelte/store';
import { toast } from 'svelte-sonner';
import type { AnnotationCreateInput } from '$lib/api/lightly_studio_local';
import type { CuboidBox } from '$lib/components/PointCloudLabelingWorkspace/CuboidDraft';
import { CUBOID_SOURCE_MESSAGES, type CuboidTarget } from '../useCuboidTargetSource';

interface SceneFrame {
    frameId: string;
}

interface Params {
    /** The annotation source new cuboids go to. */
    getTarget: () => CuboidTarget;
    getCollectionId: () => string | undefined;
    getDatasetId: () => string;
    getTickSampleId: () => string | undefined;
    getSceneFrame: () => SceneFrame | null;
}

type TrackSelection = NonNullable<
    Parameters<ReturnType<typeof useSelectClassDialog>['handleConfirm']>[1]
>;

interface CreateCuboidParams {
    frame: SceneFrame | null;
    box: CuboidBox;
    labelId: string;
    sampleId: string;
    sourceName: string;
    track?: TrackSelection;
}

interface UseCreateCuboidAnnotationReturn {
    handleCreateCuboid: (
        box: CuboidBox,
        onCreated: (annotationId: string) => void | Promise<void>,
        selectClass?: boolean
    ) => Promise<void>;
    showSelectClassDialog: ReturnType<typeof useSelectClassDialog>['open'];
    handleClassSelected: ReturnType<typeof useSelectClassDialog>['handleConfirm'];
    handleClassDialogCancel: ReturnType<typeof useSelectClassDialog>['handleCancel'];
    /** The class remembered for the collection, preselected in the class dialog. */
    getRememberedLabel: () => string | undefined;
    labels: ReturnType<typeof useAnnotationLabels>;
    tracks: ReturnType<typeof useTracks>;
}

function buildCuboidInput({
    frame,
    box,
    labelId,
    sampleId,
    sourceName,
    track
}: CreateCuboidParams): AnnotationCreateInput {
    return {
        parent_sample_id: sampleId,
        annotation_type: 'cuboid_3d',
        annotation_label_id: labelId,
        annotation_collection_name: sourceName,
        object_track_id: track?.objectTrackId ?? undefined,
        create_new_track: track?.isNewTrack ?? false,
        cuboid_3d: {
            frame_id: frame?.frameId ?? '',
            px: box.center[0],
            py: box.center[1],
            pz: box.center[2],
            // The heading is a rotation around the vertical axis.
            qx: 0,
            qy: 0,
            qz: Math.sin(box.yaw / 2),
            qw: Math.cos(box.yaw / 2),
            sx: box.size[0],
            sy: box.size[1],
            sz: box.size[2]
        }
    };
}

/** Creates point-cloud cuboids using the last selected annotation class when available. */
export function useCreateCuboidAnnotation({
    getTarget,
    getCollectionId,
    getDatasetId,
    getTickSampleId,
    getSceneFrame
}: Params): UseCreateCuboidAnnotationReturn {
    const {
        open: showSelectClassDialog,
        requestLabel,
        handleConfirm: handleClassSelected,
        handleCancel: handleClassDialogCancel
    } = useSelectClassDialog();
    const { createLabel } = useCreateLabel({ getCollectionId: () => getCollectionId() ?? '' });
    const { createAnnotation } = useCreateAnnotation({
        getCollectionId: () => getCollectionId() ?? ''
    });
    const labels = useAnnotationLabels(() => ({ collectionId: getCollectionId() ?? '' }));
    const tracks = useTracks(() => getDatasetId());
    const { lastAnnotationLabel, updateLastAnnotationLabel } = useGlobalStorage();

    async function selectAnnotationLabel(
        collectionId: string,
        selectClass: boolean
    ): Promise<{ label: string; track?: TrackSelection } | null> {
        const stored = get(lastAnnotationLabel)[collectionId] ?? null;
        if (stored && !selectClass) return { label: stored };
        const selection = await requestLabel();
        if (!selection?.label) return null;
        updateLastAnnotationLabel(collectionId, selection.label);
        return { label: selection.label, track: selection.track };
    }

    function forgetLastAnnotationLabel(collectionId: string) {
        lastAnnotationLabel.update((value) => {
            delete value[collectionId];
            return value;
        });
    }

    async function findOrCreateLabelId(
        collectionId: string,
        labelName: string
    ): Promise<string | null> {
        let currentData = labels.data;
        if (currentData === undefined) {
            const result = await labels.refetch();
            if (result.isError || result.data === undefined) return null;
            currentData = result.data;
        }
        const existingLabel = currentData?.find(
            (label) => label.annotation_label_name === labelName
        );
        if (existingLabel?.annotation_label_id) return existingLabel.annotation_label_id;
        try {
            const label = await createLabel({
                dataset_id: getDatasetId(),
                annotation_label_name: labelName
            });
            await labels.refetch();
            return label.annotation_label_id ?? null;
        } catch (error) {
            // Forget a rejected class, so the next attempt asks for a class again.
            if (error instanceof AnnotationClassNotAvailableError) {
                forgetLastAnnotationLabel(collectionId);
            }
            toast.error(
                getCreateLabelErrorMessage(
                    error,
                    'Failed to create annotation class. Please try again.'
                )
            );
            return null;
        }
    }

    async function saveCuboid(params: CreateCuboidParams): Promise<string> {
        const annotation = await createAnnotation(buildCuboidInput(params));
        toast.success(`Cuboid added to ${params.sourceName}`);
        return annotation.sample_id;
    }

    /** Returns the source for a new cuboid, or null after telling the user why there is none. */
    function getTargetSourceOrExplain(): string | null {
        const { targetSource, blockedReason, needsPick } = getTarget();
        if (blockedReason) toast.error(blockedReason);
        else if (needsPick) toast.error(CUBOID_SOURCE_MESSAGES.pick);
        return targetSource;
    }

    function getRememberedLabel(): string | undefined {
        const collectionId = getCollectionId();
        return collectionId ? get(lastAnnotationLabel)[collectionId] : undefined;
    }

    function isBlocked(): boolean {
        const { blockedReason } = getTarget();
        if (blockedReason) toast.error(blockedReason);
        return blockedReason !== null;
    }

    /**
     * Asks for the class and the track when needed and returns the class ID and the track, or
     * null when the cuboid is cancelled.
     */
    async function selectLabelAndTrack(
        collectionId: string,
        sampleId: string,
        selectClass: boolean
    ): Promise<{ labelId: string; track?: TrackSelection } | null> {
        // The dialog also asks for the source when none is picked.
        const askInDialog = selectClass || getTarget().needsPick;
        const selection = await selectAnnotationLabel(collectionId, askInDialog);
        // Cancel if the active tick changed while the class dialog was open.
        if (!selection || getTickSampleId() !== sampleId) return null;
        const labelId = await findOrCreateLabelId(collectionId, selection.label);
        // Cancel if the active sample or collection changed while finding or creating the label.
        const isSameScene = getTickSampleId() === sampleId && getCollectionId() === collectionId;
        return labelId && isSameScene ? { labelId, track: selection.track } : null;
    }

    async function trySaveCuboid(params: CreateCuboidParams): Promise<string | null> {
        try {
            return await saveCuboid(params);
        } catch {
            toast.error('Failed to create annotation. Please try again.');
            return null;
        }
    }

    async function notifyCreated(
        onCreated: (annotationId: string) => void | Promise<void>,
        annotationId: string
    ): Promise<void> {
        try {
            await Promise.all([onCreated(annotationId), tracks.refetch()]);
        } catch {
            toast.error(
                'Annotation created, but the workspace could not refresh. Please try again.'
            );
        }
    }

    async function handleCreateCuboid(
        box: CuboidBox,
        onCreated: (annotationId: string) => void | Promise<void>,
        selectClass = false
    ): Promise<void> {
        const collectionId = getCollectionId();
        const sampleId = getTickSampleId();
        const frame = getSceneFrame();
        if (!collectionId || !sampleId || isBlocked()) return;
        const selection = await selectLabelAndTrack(collectionId, sampleId, selectClass);
        if (!selection) return;
        // The user can change the source while the class dialog is open.
        const sourceName = getTargetSourceOrExplain();
        if (!sourceName) return;
        const { labelId, track } = selection;
        const annotationId = await trySaveCuboid({
            frame,
            box,
            labelId,
            sampleId,
            sourceName,
            track
        });
        if (annotationId) await notifyCreated(onCreated, annotationId);
    }

    return {
        handleCreateCuboid,
        getRememberedLabel,
        showSelectClassDialog,
        handleClassSelected,
        handleClassDialogCancel,
        labels,
        tracks
    };
}
