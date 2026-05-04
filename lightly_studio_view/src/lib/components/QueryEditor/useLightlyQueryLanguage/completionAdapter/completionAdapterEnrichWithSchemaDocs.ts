import type * as monaco from 'monaco-editor';
import { SCOPES, findFieldInScope, findKeyword } from '../../language/lightly-query-schema';

/** Fill missing docs/detail for completion items from query schema metadata. */
export function enrichWithSchemaDocs<S extends keyof typeof SCOPES>(
    item: monaco.languages.CompletionItem,
    scope: S
): monaco.languages.CompletionItem {
    if (item.documentation) return item;
    const label = typeof item.label === 'string' ? item.label : item.label.label;

    const keyword = findKeyword(label);
    if (keyword) {
        return {
            ...item,
            detail: keyword.description,
            documentation: { value: keyword.description }
        };
    }

    const field = findFieldInScope(scope, label);
    if (field) {
        return {
            ...item,
            detail: `(field) ${SCOPES[scope].title}.${field.name}: ${field.type}`,
            documentation: { value: field.description }
        };
    }

    return item;
}
