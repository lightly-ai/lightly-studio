import type { PanelType } from '$lib/hooks/useGlobalStorage';

interface PanelVisibilityOptions {
    isImages: boolean;
    hasMediaWithEmbeddings: boolean;
    supportsDistribution: boolean;
    supportsQuery?: boolean;
}

export function isPanelVisible(
    activePanel: PanelType,
    {
        isImages,
        hasMediaWithEmbeddings,
        supportsDistribution,
        supportsQuery = isImages
    }: PanelVisibilityOptions
): boolean {
    return (
        (activePanel === 'evaluationRuns' && isImages) ||
        (activePanel === 'embeddingPlot' && hasMediaWithEmbeddings) ||
        (activePanel === 'queryEditor' && supportsQuery) ||
        (activePanel === 'distribution' && supportsDistribution)
    );
}
