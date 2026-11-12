import type * as monaco from 'monaco-editor';
import { getQuerySource } from '../language/getQuerySource';

// Providers are shared across editors; scope belongs to each model.
export const modelSampleTypes = new WeakMap<monaco.editor.ITextModel, 'image' | 'video'>();

export function getModelQuerySource(model: monaco.editor.ITextModel) {
    return getQuerySource(model.getValue(), modelSampleTypes.get(model));
}
