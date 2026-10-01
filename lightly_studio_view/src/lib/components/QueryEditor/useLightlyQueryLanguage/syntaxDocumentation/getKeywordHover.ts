import * as monaco from 'monaco-editor';
import { findKeyword } from '../../language/lightly-query-schema';
import { buildKeywordHover } from './buildKeywordHover';
import { getWordRange } from './getWordRange';

/** Return keyword hover at cursor position. */
export function getKeywordHover(
    model: monaco.editor.ITextModel,
    position: monaco.Position
): monaco.languages.Hover | null {
    const word = model.getWordAtPosition(position);
    if (!word) return null;

    const keyword = findKeyword(word.word);
    if (!keyword) return null;

    return buildKeywordHover(keyword, getWordRange(position, word));
}
