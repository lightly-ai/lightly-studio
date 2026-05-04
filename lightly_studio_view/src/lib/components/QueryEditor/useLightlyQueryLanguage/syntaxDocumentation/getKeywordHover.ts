import * as monaco from 'monaco-editor';
import { findKeyword } from '../../language/lightly-query-schema';
import { buildKeywordHover } from './buildKeywordHover';
import { getWordRange } from './getWordRange';
import { resolveKeywordToken } from './resolveKeywordToken';

/** Return keyword hover at cursor position, including keywords with trailing punctuation like `video:`. */
export function getKeywordHover(
    model: monaco.editor.ITextModel,
    position: monaco.Position
): monaco.languages.Hover | null {
    const word = model.getWordAtPosition(position);
    if (!word) return null;

    const wordRange = getWordRange(position, word);
    const { keywordName, keywordRange } = resolveKeywordToken(model, position, word);
    const keyword = findKeyword(keywordName) ?? findKeyword(word.word);
    if (!keyword) return null;

    return buildKeywordHover(keyword, keyword.name === keywordName ? keywordRange : wordRange);
}
