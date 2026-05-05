import * as monaco from 'monaco-editor';
import { getWordRange } from './getWordRange';

/** Resolve keyword text and range, including punctuation Monaco omits from word tokens (e.g. `video:`). */
export function resolveKeywordToken(
    model: monaco.editor.ITextModel,
    position: monaco.Position,
    word: monaco.editor.IWordAtPosition
): { keywordName: string; keywordRange: monaco.Range } {
    const { lineNumber } = position;
    const nextChar = model.getValueInRange({
        startLineNumber: lineNumber,
        startColumn: word.endColumn,
        endLineNumber: lineNumber,
        endColumn: word.endColumn + 1
    });
    const hasColonSuffix = nextChar === ':';
    const keywordName = hasColonSuffix ? `${word.word}:` : word.word;
    const keywordRange = hasColonSuffix
        ? new monaco.Range(lineNumber, word.startColumn, lineNumber, word.endColumn + 1)
        : getWordRange(position, word);
    return { keywordName, keywordRange };
}
