/** Module to attach Monaco syntax completion */
import * as monaco from 'monaco-editor';
import {
    SCOPES,
    detectScopeAt,
    findFieldInScope,
    findKeyword
} from '../language/lightly-query-schema';

function getHover(
    model: monaco.editor.ITextModel,
    position: monaco.Position
): monaco.languages.Hover | null {
    const word = model.getWordAtPosition(position);
    if (!word) return null;

    const range = new monaco.Range(
        position.lineNumber,
        word.startColumn,
        position.lineNumber,
        word.endColumn
    );

    // Some keywords end in punctuation that Monaco strips from word extraction
    // (e.g. `video:`). Peek one char past the word so the lookup and the hover
    // range both cover the trailing `:`.
    const nextChar = model.getValueInRange({
        startLineNumber: position.lineNumber,
        startColumn: word.endColumn,
        endLineNumber: position.lineNumber,
        endColumn: word.endColumn + 1
    });
    const hasColonSuffix = nextChar === ':';
    const keywordName = hasColonSuffix ? `${word.word}:` : word.word;
    const keywordRange = hasColonSuffix
        ? new monaco.Range(
              position.lineNumber,
              word.startColumn,
              position.lineNumber,
              word.endColumn + 1
          )
        : range;

    const keyword = findKeyword(keywordName) ?? findKeyword(word.word);
    if (keyword) {
        return {
            contents: [{ value: `**${keyword.name}** — ${keyword.description}` }],
            range: keyword.name === keywordName ? keywordRange : range
        };
    }

    const text = model.getValue();
    const offset = model.getOffsetAt({
        lineNumber: position.lineNumber,
        column: word.startColumn
    });
    const scope = detectScopeAt(text, offset);
    const field = findFieldInScope(scope, word.word);
    if (!field) return null;

    const scopeDoc = SCOPES[scope];
    return {
        contents: [
            { value: `\`\`\`\n${scopeDoc.title}.${field.name}: ${field.type}\n\`\`\`` },
            { value: field.description }
        ],
        range
    };
}

// Registers the Monaco hover provider for the LightlyQuery language. Must be
// called exactly once per language id (e.g. from one-time editor setup).
// Monaco merges results from every registered provider, so calling this more
// than once produces duplicated hover content.
export function useSyntaxDocumentation(params: { languageId: string }) {
    monaco.languages.registerHoverProvider(params.languageId, {
        provideHover: (model, position) => getHover(model, position)
    });
}
