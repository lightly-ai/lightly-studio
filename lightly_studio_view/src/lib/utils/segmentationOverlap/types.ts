import type { AnnotationUpdateInput, AnnotationView } from '$lib/api/lightly_studio_local';

export type CommonParams = {
    lockedAnnotationIds?: Set<string>;
    annotations: AnnotationView[] | undefined;
    sample: { width: number; height: number };
};

export type RemoveOverlapParams = CommonParams & {
    newMask: Uint8Array;
    skipId?: string;
    segmentationMode: 'instance' | 'semantic';
    collectionId: string;
    updateAnnotations: (updates: AnnotationUpdateInput[]) => Promise<unknown>;
};

export type StripLockedParams = CommonParams & { mask: Uint8Array };

export type ApplyMaskConstraintsParams = Omit<RemoveOverlapParams, 'newMask'> & {
    workingMask: Uint8Array;
};
