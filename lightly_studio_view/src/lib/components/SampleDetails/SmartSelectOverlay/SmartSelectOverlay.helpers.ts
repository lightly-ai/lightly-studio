import type { normalizedPointFromEvent } from '$lib/components/SampleDetails/useDragBox/useDragBox.helpers';

export type SmartSelectPoint = ReturnType<typeof normalizedPointFromEvent> & { positive: boolean };

// The provider rejects point prompts without a positive point.
export const canInferFromPoints = (points: SmartSelectPoint[]): boolean =>
    points.some((point) => point.positive);
