import * as monaco from 'monaco-editor';
import {
    InsertTextFormat as LspInsertTextFormat,
    type CompletionItem as LspCompletionItem
} from 'vscode-languageserver-types';
import { SCOPES } from '../../language/lightly-query-schema';
import { enrichWithSchemaDocs } from './completionAdapterEnrichWithSchemaDocs';
import { mapDocumentation } from './completionAdapterMapDocumentation';
import { LSP_TO_MONACO_KIND } from './completionAdapterShared';

function toMonacoRange(range: {
    start: { line: number; character: number };
    end: { line: number; character: number };
}): monaco.IRange {
    // LSP positions are 0-based (line/character), Monaco ranges are 1-based.
    return {
        startLineNumber: range.start.line + 1,
        startColumn: range.start.character + 1,
        endLineNumber: range.end.line + 1,
        endColumn: range.end.character + 1
    };
}

/** Adapt one LSP completion item into Monaco completion shape. */
export function lspToMonacoCompletion<Scope extends keyof typeof SCOPES>(
    item: LspCompletionItem,
    fallbackRange: monaco.IRange,
    scope: Scope
): monaco.languages.CompletionItem {
    const { label, kind, detail, documentation, sortText, filterText, textEdit } = item;
    const isSnippet = item.insertTextFormat === LspInsertTextFormat.Snippet;

    let range: monaco.IRange | monaco.languages.CompletionItemRanges = fallbackRange;
    let insertText = item.insertText ?? label;
    if (textEdit && 'range' in textEdit) {
        range = toMonacoRange(textEdit.range);
        insertText = textEdit.newText;
    } else if (textEdit && 'insert' in textEdit && 'replace' in textEdit) {
        // InsertReplaceEdit: preserve dual-range semantics so Monaco can insert
        // when typing in-place and replace when completing over a wider span.
        range = {
            insert: toMonacoRange(textEdit.insert),
            replace: toMonacoRange(textEdit.replace)
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
