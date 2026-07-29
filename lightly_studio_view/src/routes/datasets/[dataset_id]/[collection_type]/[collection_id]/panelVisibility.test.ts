import { describe, it, expect } from 'vitest';
import { isPanelVisible } from './panelVisibility';

describe('isPanelVisible', () => {
    it('no panel is visible when activePanel is "none"', () => {
        expect(isPanelVisible('none', true, true)).toBe(false);
    });

    it('evaluationRuns panel is visible on images route', () => {
        expect(isPanelVisible('evaluationRuns', true, false)).toBe(true);
    });

    it('evaluationRuns panel is NOT visible on non-images routes', () => {
        expect(isPanelVisible('evaluationRuns', false, false)).toBe(false);
    });

    it('embeddingPlot panel is visible on images route when embeddings exist', () => {
        expect(isPanelVisible('embeddingPlot', true, true)).toBe(true);
    });

    it('embeddingPlot panel is NOT visible when there are no embeddings', () => {
        expect(isPanelVisible('embeddingPlot', true, false)).toBe(false);
    });

    it('embeddingPlot panel is NOT visible on non-images route without embeddings', () => {
        expect(isPanelVisible('embeddingPlot', false, false)).toBe(false);
    });

    it('queryEditor panel is visible on images route only', () => {
        expect(isPanelVisible('queryEditor', true, false)).toBe(true);
        expect(isPanelVisible('queryEditor', false, false)).toBe(false);
    });

    it('distribution panel is visible on images route only', () => {
        expect(isPanelVisible('distribution', true, false)).toBe(true);
        expect(isPanelVisible('distribution', false, false)).toBe(false);
    });
});
