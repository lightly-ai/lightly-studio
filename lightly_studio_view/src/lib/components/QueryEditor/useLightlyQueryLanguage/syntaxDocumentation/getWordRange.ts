import * as monaco from 'monaco-editor';

/** Build the Monaco range that spans the word currently under the cursor. */
export function getWordRange(
    position: monaco.Position,
    word: monaco.editor.IWordAtPosition
): monaco.Range {
    const { lineNumber } = position;
    return new monaco.Range(lineNumber, word.startColumn, lineNumber, word.endColumn);
}
