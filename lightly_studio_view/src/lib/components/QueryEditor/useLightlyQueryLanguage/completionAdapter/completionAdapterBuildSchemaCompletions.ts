import * as monaco from 'monaco-editor';
import { SCOPES, TOP_LEVEL_KEYWORDS, BOOLEAN_KEYWORDS } from '../../language/lightly-query-schema';
import { ALLOWED_NESTED_KEYWORDS } from './completionAdapterShared';

/** Build scope-aware schema fallback completion items. */
export function buildSchemaCompletions<Scope extends keyof typeof SCOPES>(
    scope: Scope,
    range: monaco.IRange,
    includeBooleanLiterals = false
): monaco.languages.CompletionItem[] {
    const items: monaco.languages.CompletionItem[] = [];
    const { title, fields } = SCOPES[scope];

    for (const field of fields) {
        items.push({
            label: field.name,
            kind: monaco.languages.CompletionItemKind.Field,
            detail: `${title}.${field.name}: ${field.type}`,
            documentation: { value: field.description },
            insertText: field.name,
            range
        });
    }

    const keywords = [
        ...TOP_LEVEL_KEYWORDS,
        ...(includeBooleanLiterals ? BOOLEAN_KEYWORDS : [])
    ].filter((kw) => {
        if (scope === 'image' || scope === 'video') return kw.name !== 'video:';
        return ALLOWED_NESTED_KEYWORDS.has(kw.name);
    });

    for (const kw of keywords) {
        const insertText = kw.insertText ?? kw.name;
        const isSnippet = insertText.includes('$');
        items.push({
            label: kw.name,
            sortText: BOOLEAN_KEYWORDS.includes(kw) ? '0' : undefined,
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
