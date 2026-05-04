import * as monaco from 'monaco-editor';
import { SCOPES } from '../../language/lightly-query-schema';

/** Build hover content for a field in a resolved scope, including type and description. */
export function buildFieldHover<S extends keyof typeof SCOPES>(
    scope: S,
    field: (typeof SCOPES)[S]['fields'][number],
    range: monaco.Range
): monaco.languages.Hover {
    const { title } = SCOPES[scope];
    return {
        contents: [
            { value: `\`\`\`\n${title}.${field.name}: ${field.type}\n\`\`\`` },
            { value: field.description }
        ],
        range
    };
}
