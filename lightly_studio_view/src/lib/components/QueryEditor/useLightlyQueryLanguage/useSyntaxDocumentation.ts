/** Module to attach Monaco syntax completion */
import * as monaco from 'monaco-editor';
import { findFieldByName, findReceiverByName } from '../language/lightly-query-schema';

function getHover(
    model: monaco.editor.ITextModel,
    position: monaco.Position
): monaco.languages.Hover | null {
    const word = model.getWordAtPosition(position);
    if (!word) return null;

    const line = model.getLineContent(position.lineNumber);
    const cursorOffset = position.column - 1;

    const qualifiedReference = /([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)/g;
    let match: RegExpExecArray | null;
    while ((match = qualifiedReference.exec(line))) {
        const fullStart = match.index;
        const fullEnd = match.index + match[0].length;
        if (cursorOffset < fullStart || cursorOffset > fullEnd) continue;

        const receiver = findReceiverByName(match[1]);
        if (!receiver) continue;

        const memberStart = match.index + match[1].length + 1;
        if (cursorOffset >= memberStart) {
            const field = findFieldByName(receiver, match[2]);
            if (!field) return null;
            return {
                contents: [
                    { value: `\`\`\`\n${receiver.name}.${field.name}: ${field.type}\n\`\`\`` },
                    { value: field.description }
                ],
                range: new monaco.Range(
                    position.lineNumber,
                    memberStart + 1,
                    position.lineNumber,
                    memberStart + 1 + match[2].length
                )
            };
        }
        return {
            contents: [{ value: `**${receiver.name}** — ${receiver.description}` }],
            range: new monaco.Range(
                position.lineNumber,
                fullStart + 1,
                position.lineNumber,
                fullStart + 1 + match[1].length
            )
        };
    }

    const receiver = findReceiverByName(word.word);
    if (receiver) {
        return {
            contents: [{ value: `**${receiver.name}** — ${receiver.description}` }],
            range: new monaco.Range(
                position.lineNumber,
                word.startColumn,
                position.lineNumber,
                word.endColumn
            )
        };
    }
    return null;
}

/**
 * Hook to attach syntax completion
 */
export function useSyntaxDocumentation(params: { languageId: string }) {
    monaco.languages.registerHoverProvider(params.languageId, {
        provideHover: (model, position) => getHover(model, position)
    });
}
