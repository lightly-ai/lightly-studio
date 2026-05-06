import type * as monaco from 'monaco-editor';
import {
    type CompletionItem as LspCompletionItem,
    type MarkupContent
} from 'vscode-languageserver-types';

/** Map LSP documentation payloads into Monaco hover markdown payloads. */
export function mapDocumentation(
    doc: LspCompletionItem['documentation']
): string | monaco.IMarkdownString | undefined {
    if (!doc) return undefined;
    if (typeof doc === 'string') return doc;
    return { value: (doc as MarkupContent).value };
}
