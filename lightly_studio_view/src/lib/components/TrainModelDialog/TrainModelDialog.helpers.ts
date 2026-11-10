import type { TrainingRunView } from '$lib/api/lightly_studio_local/types.gen';

type TrainingRunStatus = TrainingRunView['status'];

const ACTIVE_STATUSES: TrainingRunStatus[] = ['training', 'predicting', 'ingesting', 'evaluating'];

export const STATUS_LABELS: Record<TrainingRunStatus, string> = {
    training: 'Training',
    predicting: 'Predicting on all images',
    ingesting: 'Adding predictions',
    evaluating: 'Evaluating on the val tag',
    completed: 'Completed',
    failed: 'Failed',
    cancelled: 'Cancelled'
};

export const TRAINING_MODELS = [
    { value: 'dinov3/vitt16-ltdetr-coco', label: 'DINOv3 ViT-T/16 LTDETR (fastest)' },
    { value: 'dinov3/convnext-tiny-ltdetr-coco', label: 'DINOv3 ConvNeXt-T LTDETR' },
    { value: 'ltdetrv2-s-coco', label: 'LTDETRv2-S' }
];

export const DEFAULT_TRAINING_STEPS = 100;

export const isActiveRun = (run: Pick<TrainingRunView, 'status'> | undefined): boolean =>
    !!run && ACTIVE_STATUSES.includes(run.status);

export const progressPercent = (
    run: Pick<TrainingRunView, 'current_step' | 'total_steps'>
): number | null => {
    if (!run.current_step || !run.total_steps) return null;
    return Math.min(100, Math.round((100 * run.current_step) / run.total_steps));
};

interface CanStartTrainingParams {
    trainTagId?: string;
    valTagId?: string;
    gtSourceId?: string;
    steps: number;
    isStarting: boolean;
}

export const canStartTraining = (params: CanStartTrainingParams): boolean =>
    !!params.trainTagId &&
    !!params.valTagId &&
    params.trainTagId !== params.valTagId &&
    !!params.gtSourceId &&
    Number.isInteger(params.steps) &&
    params.steps >= 1 &&
    !params.isStarting;
