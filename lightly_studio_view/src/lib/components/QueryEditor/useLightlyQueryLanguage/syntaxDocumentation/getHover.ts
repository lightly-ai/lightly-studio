import * as monaco from 'monaco-editor';
import { getFieldHover } from './getFieldHover';
import { getKeywordHover } from './getKeywordHover';

/** Orchestrate hover resolution by preferring keyword hover and falling back to scope-aware field hover. */
export function getHover(
    model: monaco.editor.ITextModel,
    position: monaco.Position
): monaco.languages.Hover | null {
    return getKeywordHover(model, position) ?? getFieldHover(model, position);
}
