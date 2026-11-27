import * as monaco from 'monaco-editor';
import { getMetadataQueryContext } from '$lib/components/QueryEditor/language';
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
    if (keyword.name === 'metadata' || keyword.name === 'true' || keyword.name === 'false') {
        const context = getMetadataQueryContext({
            text: model.getValue(),
            offset: model.getOffsetAt({ lineNumber: position.lineNumber, column: word.startColumn })
        });
        const expectedContext = keyword.name === 'metadata' ? 'field' : 'boolean';
        if (context !== expectedContext) return null;
    }

    return buildKeywordHover(keyword, keyword.name === keywordName ? keywordRange : wordRange);
}
