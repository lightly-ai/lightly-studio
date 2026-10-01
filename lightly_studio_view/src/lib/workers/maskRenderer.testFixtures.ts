import type { RenderGeometry } from './maskRendererUtils';

export const createRenderGeometry = (overrides: Partial<RenderGeometry> = {}): RenderGeometry => ({
    sourceWidth: 100,
    sourceHeight: 100,
    outputWidth: 200,
    outputHeight: 200,
    objectFit: 'contain',
    ...overrides
});

export const createWorkerRenderMessage = (overrides: Record<string, unknown> = {}) => ({
    type: 'render',
    canvasId: 'canvas-1',
    sourceWidth: 16,
    sourceHeight: 8,
    outputWidth: 8,
    outputHeight: 4,
    objectFit: 'contain',
    masks: [],
    boxes: [],
    ...overrides
});
