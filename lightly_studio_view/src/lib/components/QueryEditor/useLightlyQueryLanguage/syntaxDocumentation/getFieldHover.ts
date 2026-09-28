import * as monaco from 'monaco-editor';
import { detectScopeAt } from '../../language/detectScopeAt';
import { findFieldInScope } from '../../language/lightly-query-schema';
import { getModelRootScope } from '../modelRootScope';
import { buildFieldHover } from './buildFieldHover';
import { getWordRange } from './getWordRange';

/** Return field hover at cursor position after resolving the active query scope. */
export function getFieldHover(
    model: monaco.editor.ITextModel,
    position: monaco.Position
): monaco.languages.Hover | null {
    const word = model.getWordAtPosition(position);
    if (!word) return null;

    const text = model.getValue();
    const offset = model.getOffsetAt({
        lineNumber: position.lineNumber,
        column: word.startColumn
    });
    const scope = detectScopeAt(text, offset, getModelRootScope(model));
    const field = findFieldInScope(scope, word.word);
    if (!field) return null;

    return buildFieldHover(scope, field, getWordRange(position, word));
}
