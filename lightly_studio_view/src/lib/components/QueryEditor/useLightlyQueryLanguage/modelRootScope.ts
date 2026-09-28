/** Root scope of each Monaco model.
 *
 * Monaco registers the completion and hover providers once per language, so
 * the providers look up the root scope of the model that they serve. */
import type * as monaco from 'monaco-editor';
import type { RootScope } from '../language/types';

const rootScopes = new WeakMap<monaco.editor.ITextModel, RootScope>();

export function setModelRootScope(model: monaco.editor.ITextModel, rootScope: RootScope): void {
    rootScopes.set(model, rootScope);
}

export function getModelRootScope(model: monaco.editor.ITextModel): RootScope {
    return rootScopes.get(model) ?? 'image';
}
