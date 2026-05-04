/** Monaco <-> Langium/LSP completion bridge.
 *
 * Why this exists:
 * - Monaco completion providers consume Monaco-shaped items/ranges/docs.
 * - Langium completion providers emit LSP protocol types.
 * - This module is the isolated adapter boundary where we:
 *   1) sync Monaco model text into a Langium document,
 *   2) map LSP completion payloads into Monaco completion payloads,
 *   3) add schema-derived fallback completions that the grammar-only LSP
 *      provider cannot infer (e.g. scope-specific fields).
 */
import * as monaco from 'monaco-editor';
import { URI } from 'langium';
import {
    CompletionItemKind as LspCompletionItemKind,
    InsertTextFormat as LspInsertTextFormat,
    type CompletionItem as LspCompletionItem,
    type MarkupContent
} from 'vscode-languageserver-types';
import type { LightlyQueryServicesBundle } from '../language/lightly-query-module';
import {
    SCOPES,
    TOP_LEVEL_KEYWORDS,
    findFieldInScope,
    findKeyword,
    type Scope
} from '../language/lightly-query-schema';

const ALLOWED_NESTED_KEYWORDS = new Set(['AND', 'OR', 'NOT']);

const MONACO_KIND = monaco.languages.CompletionItemKind;
const LSP_KIND = LspCompletionItemKind;
const LSP_TO_MONACO_KIND: Readonly<Record<number, monaco.languages.CompletionItemKind>> =
    Object.freeze({
        [LSP_KIND.Text]: MONACO_KIND.Text,
        [LSP_KIND.Method]: MONACO_KIND.Method,
        [LSP_KIND.Function]: MONACO_KIND.Function,
        [LSP_KIND.Constructor]: MONACO_KIND.Constructor,
        [LSP_KIND.Field]: MONACO_KIND.Field,
        [LSP_KIND.Variable]: MONACO_KIND.Variable,
        [LSP_KIND.Class]: MONACO_KIND.Class,
        [LSP_KIND.Interface]: MONACO_KIND.Interface,
        [LSP_KIND.Module]: MONACO_KIND.Module,
        [LSP_KIND.Property]: MONACO_KIND.Property,
        [LSP_KIND.Unit]: MONACO_KIND.Unit,
        [LSP_KIND.Value]: MONACO_KIND.Value,
        [LSP_KIND.Enum]: MONACO_KIND.Enum,
        [LSP_KIND.Keyword]: MONACO_KIND.Keyword,
        [LSP_KIND.Snippet]: MONACO_KIND.Snippet,
        [LSP_KIND.Color]: MONACO_KIND.Color,
        [LSP_KIND.File]: MONACO_KIND.File,
        [LSP_KIND.Reference]: MONACO_KIND.Reference,
        [LSP_KIND.Folder]: MONACO_KIND.Folder,
        [LSP_KIND.EnumMember]: MONACO_KIND.EnumMember,
        [LSP_KIND.Constant]: MONACO_KIND.Constant,
        [LSP_KIND.Struct]: MONACO_KIND.Struct,
        [LSP_KIND.Event]: MONACO_KIND.Event,
        [LSP_KIND.Operator]: MONACO_KIND.Operator,
        [LSP_KIND.TypeParameter]: MONACO_KIND.TypeParameter
    });

function mapDocumentation(
    doc: LspCompletionItem['documentation']
): string | monaco.IMarkdownString | undefined {
    if (!doc) return undefined;
    if (typeof doc === 'string') return doc;
    return { value: (doc as MarkupContent).value };
}

function enrichWithSchemaDocs(
    item: monaco.languages.CompletionItem,
    scope: Scope
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

export async function syncLangiumDocument(
    model: monaco.editor.ITextModel,
    services: LightlyQueryServicesBundle
) {
    const {
        shared: {
            workspace: { LangiumDocuments: documents, DocumentBuilder: builder }
        }
    } = services;

    const uri = URI.parse(model.uri.toString());
    documents.deleteDocument(uri);
    const doc = documents.createDocument(uri, model.getValue());
    await builder.build([doc], { validation: false });
    return doc;
}

export function lspToMonacoCompletion(
    item: LspCompletionItem,
    fallbackRange: monaco.IRange,
    scope: Scope
): monaco.languages.CompletionItem {
    const { label, kind, detail, documentation, sortText, filterText, textEdit } = item;
    const isSnippet = item.insertTextFormat === LspInsertTextFormat.Snippet;

    let range: monaco.IRange = fallbackRange;
    let insertText = item.insertText ?? label;
    if (textEdit && 'range' in textEdit) {
        const { range: editRange, newText } = textEdit;
        range = {
            startLineNumber: editRange.start.line + 1,
            startColumn: editRange.start.character + 1,
            endLineNumber: editRange.end.line + 1,
            endColumn: editRange.end.character + 1
        };
        insertText = newText;
    }

    return enrichWithSchemaDocs(
        {
            label,
            kind: kind
                ? (LSP_TO_MONACO_KIND[kind] ?? monaco.languages.CompletionItemKind.Text)
                : monaco.languages.CompletionItemKind.Text,
            detail,
            documentation: mapDocumentation(documentation),
            insertText,
            insertTextRules: isSnippet
                ? monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet
                : undefined,
            range,
            sortText,
            filterText
        },
        scope
    );
}

export function buildSchemaCompletions(
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
