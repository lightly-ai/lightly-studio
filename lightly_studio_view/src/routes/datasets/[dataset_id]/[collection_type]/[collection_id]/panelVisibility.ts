import type { PanelType } from '$lib/hooks/useGlobalStorage';

export function isPanelVisible(
    activePanel: PanelType,
    isImages: boolean,
    hasMediaWithEmbeddings: boolean,
    supportsDistribution: boolean,
    supportsQuery: boolean
): boolean {
    return (
        (activePanel === 'evaluationRuns' && isImages) ||
        (activePanel === 'embeddingPlot' && hasMediaWithEmbeddings) ||
        (activePanel === 'queryEditor' && supportsQuery) ||
        (activePanel === 'distribution' && supportsDistribution)
    );
}
