// These are the coefficients we obtained from  experiments (do not change!)
const PREPARATION_SECONDS_PER_CANDIDATE_DIMENSION = 2.7628712026803005e-7;
const SELECTION_SECONDS_PER_CANDIDATE_SELECTION_DIMENSION = 1.303255247136871e-10;

// The min time is our estimate (based on M1 Apple Silicon)
// We use a premium multiplier to obtain a max processing time
const PREMIUM_MULTIPLIER = 1.6;

interface SamplingEstimateInput {
    candidateCount: number;
    selectionCount: number;
    strategyCount: number;
    embeddingDimension: number;
}

export interface SamplingEstimate {
    runtimeSeconds: {
        base: number;
        premium: number;
    };
}

export interface FrozenSamplingRun {
    estimate: SamplingEstimate;
    startedAt: Date;
}

export function estimateSampling({
    candidateCount,
    selectionCount,
    strategyCount,
    embeddingDimension
}: SamplingEstimateInput): SamplingEstimate | null {
    const values = [candidateCount, selectionCount, strategyCount, embeddingDimension];
    if (values.some((value) => !Number.isFinite(value) || value <= 0)) return null;
    if (selectionCount > candidateCount) return null;

    const preparationFeature = candidateCount * embeddingDimension;
    const selectionFeature = preparationFeature * selectionCount;
    const perStrategyRuntime =
        PREPARATION_SECONDS_PER_CANDIDATE_DIMENSION * preparationFeature +
        SELECTION_SECONDS_PER_CANDIDATE_SELECTION_DIMENSION * selectionFeature;
    const runtimeBase = perStrategyRuntime * strategyCount;

    return {
        runtimeSeconds: { base: runtimeBase, premium: runtimeBase * PREMIUM_MULTIPLIER }
    };
}

export function formatDuration(seconds: number): string {
    if (seconds < 1) return '<1 sec';
    if (seconds < 60) return `${Math.ceil(seconds)} sec`;

    const minutes = Math.ceil(seconds / 60);
    if (minutes < 60) return `${minutes} min`;
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;
    return remainingMinutes === 0 ? `${hours} hr` : `${hours} hr ${remainingMinutes} min`;
}

export function formatRange(
    bounds: SamplingEstimate['runtimeSeconds'],
    formatter: (value: number) => string
): string {
    const base = formatter(bounds.base);
    const premium = formatter(bounds.premium);
    return base === premium ? base : `${base}–${premium}`;
}

export function formatLocalTime(date: Date, showSeconds: boolean): string {
    return date.toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit',
        ...(showSeconds ? { second: '2-digit' } : {})
    });
}

export function estimateFinish(run: FrozenSamplingRun): Date {
    return new Date(run.startedAt.getTime() + run.estimate.runtimeSeconds.premium * 1_000);
}
