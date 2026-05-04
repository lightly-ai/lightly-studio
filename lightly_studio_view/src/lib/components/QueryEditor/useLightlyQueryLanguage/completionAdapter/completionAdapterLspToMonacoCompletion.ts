import * as monaco from 'monaco-editor';
import {
    InsertTextFormat as LspInsertTextFormat,
    type CompletionItem as LspCompletionItem
} from 'vscode-languageserver-types';
import { SCOPES } from '../../language/lightly-query-schema';
import { enrichWithSchemaDocs } from './completionAdapterEnrichWithSchemaDocs';
import { mapDocumentation } from './completionAdapterMapDocumentation';
import { LSP_TO_MONACO_KIND } from './completionAdapterShared';

/** Adapt one LSP completion item into Monaco completion shape. */
export function lspToMonacoCompletion<S extends keyof typeof SCOPES>(
    item: LspCompletionItem,
    fallbackRange: monaco.IRange,
    scope: S
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
