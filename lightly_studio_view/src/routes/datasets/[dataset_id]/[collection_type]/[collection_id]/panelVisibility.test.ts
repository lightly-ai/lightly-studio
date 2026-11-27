import { describe, it, expect } from 'vitest';
import { isPanelVisible } from './panelVisibility';

const defaultOptions = {
    isImages: true,
    hasMediaWithEmbeddings: false,
    supportsDistribution: true
};

describe('isPanelVisible', () => {
    it('no panel is visible when activePanel is "none"', () => {
        expect(isPanelVisible('none', { ...defaultOptions, hasMediaWithEmbeddings: true })).toBe(
            false
        );
    });

    it('evaluationRuns panel is visible on images route', () => {
        expect(isPanelVisible('evaluationRuns', defaultOptions)).toBe(true);
    });

    it('evaluationRuns panel is NOT visible on non-images routes', () => {
        expect(isPanelVisible('evaluationRuns', { ...defaultOptions, isImages: false })).toBe(
            false
        );
    });

    it('embeddingPlot panel is visible on images route when embeddings exist', () => {
        expect(
            isPanelVisible('embeddingPlot', { ...defaultOptions, hasMediaWithEmbeddings: true })
        ).toBe(true);
    });

    it('embeddingPlot panel is NOT visible when there are no embeddings', () => {
        expect(isPanelVisible('embeddingPlot', defaultOptions)).toBe(false);
    });

    it('embeddingPlot panel is NOT visible on non-images route without embeddings', () => {
        expect(isPanelVisible('embeddingPlot', { ...defaultOptions, isImages: false })).toBe(false);
    });

    it('queryEditor panel is visible on image and video grids', () => {
        expect(isPanelVisible('queryEditor', defaultOptions)).toBe(true);
        expect(
            isPanelVisible('queryEditor', {
                ...defaultOptions,
                isImages: false,
                supportsQuery: true
            })
        ).toBe(true);
        expect(isPanelVisible('queryEditor', { ...defaultOptions, isImages: false })).toBe(false);
    });

    it('distribution panel is visible only where distributions are supported', () => {
        expect(isPanelVisible('distribution', { ...defaultOptions, isImages: false })).toBe(true);
        expect(
            isPanelVisible('distribution', { ...defaultOptions, supportsDistribution: false })
        ).toBe(false);
    });

    it('agentChat panel is visible only when the agent is switched on', () => {
        expect(isPanelVisible('agentChat', { ...defaultOptions, supportsAgentChat: true })).toBe(
            true
        );
        expect(isPanelVisible('agentChat', defaultOptions)).toBe(false);
    });
});
