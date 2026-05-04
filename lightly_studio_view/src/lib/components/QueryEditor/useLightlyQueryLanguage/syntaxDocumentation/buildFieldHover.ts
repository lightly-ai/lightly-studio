import * as monaco from 'monaco-editor';
import { SCOPES } from '../../language/lightly-query-schema';

/** Build hover content for a field in a resolved scope, including type and description. */
export function buildFieldHover<
    Scope extends keyof typeof SCOPES,
    FieldDoc extends (typeof SCOPES)[Scope]['fields'][number]
>(scope: Scope, field: FieldDoc, range: monaco.Range): monaco.languages.Hover {
    const { title } = SCOPES[scope];
    return {
        contents: [
            { value: `\`\`\`\n${title}.${field.name}: ${field.type}\n\`\`\`` },
            { value: field.description }
        ],
        range
    };
}
