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

    const keyword = findKeyword(word.word);
    if (keyword) {
        return {
            contents: [{ value: `**${keyword.name}** — ${keyword.description}` }],
            range
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
