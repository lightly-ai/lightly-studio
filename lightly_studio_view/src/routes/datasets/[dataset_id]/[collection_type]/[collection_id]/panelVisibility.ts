import type { PanelType } from '$lib/hooks/useGlobalStorage';

export function isPanelVisible(
    activePanel: PanelType,
    isImages: boolean,
    hasMediaWithEmbeddings: boolean
): boolean {
    return (
        (activePanel === 'evaluationRuns' && isImages) ||
        (activePanel === 'embeddingPlot' && hasMediaWithEmbeddings) ||
        (activePanel === 'queryEditor' && isImages) ||
        (activePanel === 'distribution' && isImages)
    );
}
