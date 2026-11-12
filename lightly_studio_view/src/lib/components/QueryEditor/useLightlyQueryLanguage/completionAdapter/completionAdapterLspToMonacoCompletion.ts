import * as monaco from 'monaco-editor';
import {
    InsertTextFormat as LspInsertTextFormat,
    type CompletionItem as LspCompletionItem
} from 'vscode-languageserver-types';
import { SCOPES } from '../../language/lightly-query-schema';
import { enrichWithSchemaDocs } from './completionAdapterEnrichWithSchemaDocs';
import { mapDocumentation } from './completionAdapterMapDocumentation';
import { LSP_TO_MONACO_KIND } from './completionAdapterShared';

function toMonacoRange(
    range: {
        start: { line: number; character: number };
        end: { line: number; character: number };
    },
    lineOffset: number
): monaco.IRange {
    // LSP positions are 0-based (line/character), Monaco ranges are 1-based.
    return {
        startLineNumber: Math.max(1, range.start.line + 1 - lineOffset),
        startColumn: range.start.character + 1,
        endLineNumber: Math.max(1, range.end.line + 1 - lineOffset),
        endColumn: range.end.character + 1
    };
}

/** Adapt one LSP completion item into Monaco completion shape. */
export function lspToMonacoCompletion<Scope extends keyof typeof SCOPES>(
    item: LspCompletionItem,
    fallbackRange: monaco.IRange,
    scope: Scope,
    lineOffset = 0
): monaco.languages.CompletionItem {
    const { label, kind, detail, documentation, sortText, filterText, textEdit } = item;
    const isSnippet = item.insertTextFormat === LspInsertTextFormat.Snippet;

    let range: monaco.IRange | monaco.languages.CompletionItemRanges = fallbackRange;
    let insertText = item.insertText ?? label;
    if (textEdit) {
        // InsertReplaceEdit: preserve dual-range semantics so Monaco can insert
        // when typing in-place and replace when completing over a wider span.
        range =
            'range' in textEdit
                ? toMonacoRange(textEdit.range, lineOffset)
                : {
                      insert: toMonacoRange(textEdit.insert, lineOffset),
                      replace: toMonacoRange(textEdit.replace, lineOffset)
                  };
        insertText = textEdit.newText;
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
