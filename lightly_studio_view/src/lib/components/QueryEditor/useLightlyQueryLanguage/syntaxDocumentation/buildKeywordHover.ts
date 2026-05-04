import * as monaco from 'monaco-editor';
import type { KeywordDoc } from '../../language/types';

/** Build hover content for a language keyword using its schema description. */
export function buildKeywordHover(
    keyword: KeywordDoc,
    range: monaco.Range
): monaco.languages.Hover {
    return {
        contents: [{ value: `**${keyword.name}** — ${keyword.description}` }],
        range
    };
}
