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

// Monaco merges results from every registered HoverProvider, so registering
// per editor mount produces N copies of the same hover content. Track which
// language ids we've already wired up and skip the duplicate registration.
const registeredLanguageIds = new Set<string>();

/**
 * Hook to attach syntax completion
 */
export function useSyntaxDocumentation(params: { languageId: string }) {
    if (registeredLanguageIds.has(params.languageId)) return;
    registeredLanguageIds.add(params.languageId);
    monaco.languages.registerHoverProvider(params.languageId, {
        provideHover: (model, position) => getHover(model, position)
    });
}
