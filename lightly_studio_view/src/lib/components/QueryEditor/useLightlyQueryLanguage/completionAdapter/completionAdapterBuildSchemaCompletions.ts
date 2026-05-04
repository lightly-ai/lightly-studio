import * as monaco from 'monaco-editor';
import { SCOPES, TOP_LEVEL_KEYWORDS } from '../../language/lightly-query-schema';
import { ALLOWED_NESTED_KEYWORDS } from './completionAdapterShared';

/** Build scope-aware schema fallback completion items. */
export function buildSchemaCompletions<Scope extends keyof typeof SCOPES>(
    scope: Scope,
    range: monaco.IRange
): monaco.languages.CompletionItem[] {
    const items: monaco.languages.CompletionItem[] = [];
    const { title, fields } = SCOPES[scope];

    for (const field of fields) {
        items.push({
            label: field.name,
            kind: monaco.languages.CompletionItemKind.Field,
            detail: `(field) ${title}.${field.name}: ${field.type}`,
            documentation: { value: field.description },
            insertText: field.name,
            range
        });
    }

    const keywords = TOP_LEVEL_KEYWORDS.filter((kw) => {
        if (scope === 'image') return true;
        if (scope === 'video') return kw.name !== 'video:';
        return ALLOWED_NESTED_KEYWORDS.has(kw.name);
    });

    for (const kw of keywords) {
        const insertText = kw.insertText ?? kw.name;
        const isSnippet = insertText.includes('$');
        items.push({
            label: kw.name,
            kind: monaco.languages.CompletionItemKind.Keyword,
            detail: kw.description,
            documentation: { value: kw.description },
            insertText,
            insertTextRules: isSnippet
                ? monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet
                : undefined,
            range
        });
    }

    return items;
}
