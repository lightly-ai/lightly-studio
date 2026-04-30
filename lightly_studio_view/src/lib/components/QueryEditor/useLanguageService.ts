/** Main-thread Langium integration for the LightlyQuery editor.
 *
 * The Langium parser, document builder, and provider classes all run directly
 * on the main thread (no worker, no LSP transport). Diagnostics are pushed
 * into Monaco via `setModelMarkers`, completions are produced by Langium's
 * own `CompletionProvider`, and `translateQuery` is a synchronous call into
 * `parseLightlyQuery`. */

import * as monaco from 'monaco-editor';
import { URI } from 'langium';
import {
    CompletionItemKind as LspCompletionItemKind,
    InsertTextFormat as LspInsertTextFormat,
    type CompletionItem as LspCompletionItem,
    type CompletionList as LspCompletionList,
    type MarkupContent
} from 'vscode-languageserver-types';
import {
    createLightlyQueryServices,
    type LightlyQueryServicesBundle
} from './language/lightly-query-module';
import {
    parseLightlyQuery,
    type QueryExprTranslationResult
} from './language/query-expr-translation';
import { RECEIVERS, type FieldDoc, type ReceiverDoc } from './language/lightly-query-schema';

const LANGUAGE_ID = 'lightly-query';
const MARKER_OWNER = LANGUAGE_ID;

let cachedServices: LightlyQueryServicesBundle | null = null;
function getServices(): LightlyQueryServicesBundle {
    if (!cachedServices) {
        cachedServices = createLightlyQueryServices();
    }
    return cachedServices;
}

interface ParserErrorLike {
    message: string;
    token?: {
        startLine?: number;
        startColumn?: number;
        endLine?: number;
        endColumn?: number;
        image?: string;
    };
}

interface LexerErrorLike {
    message: string;
    line?: number;
    column?: number;
    length?: number;
}

function lexerErrorToMarker(err: LexerErrorLike): monaco.editor.IMarkerData {
    const startLine = err.line ?? 1;
    const startColumn = err.column ?? 1;
    const length = err.length ?? 1;
    return {
        severity: monaco.MarkerSeverity.Error,
        message: err.message,
        startLineNumber: startLine,
        startColumn,
        endLineNumber: startLine,
        endColumn: startColumn + length
    };
}

function parserErrorToMarker(err: ParserErrorLike): monaco.editor.IMarkerData {
    const token = err.token;
    const startLine = token?.startLine ?? 1;
    const startColumn = token?.startColumn ?? 1;
    const endLine = token?.endLine ?? startLine;
    const endColumn = (token?.endColumn ?? startColumn) + 1;
    return {
        severity: monaco.MarkerSeverity.Error,
        message: err.message,
        startLineNumber: startLine,
        startColumn,
        endLineNumber: endLine,
        endColumn
    };
}

function findReceiverByName(name: string): ReceiverDoc | undefined {
    return RECEIVERS.find((r) => r.name === name);
}

function findFieldByName(receiver: ReceiverDoc, name: string): FieldDoc | undefined {
    return receiver.fields.find((f) => f.name === name);
}

// Build (or rebuild) the LangiumDocument backing this Monaco model so that
// Langium's providers see the latest text. Cheap for short queries; we just
// throw away and recreate on each call.
async function syncDocument(model: monaco.editor.ITextModel) {
    const services = getServices();
    const documents = services.shared.workspace.LangiumDocuments;
    const builder = services.shared.workspace.DocumentBuilder;

    const uri = URI.parse(model.uri.toString());
    documents.deleteDocument(uri);
    const doc = documents.createDocument(uri, model.getValue());
    await builder.build([doc], { validation: false });
    return doc;
}

const LSP_TO_MONACO_KIND: Record<number, monaco.languages.CompletionItemKind> = {
    [LspCompletionItemKind.Text]: monaco.languages.CompletionItemKind.Text,
    [LspCompletionItemKind.Method]: monaco.languages.CompletionItemKind.Method,
    [LspCompletionItemKind.Function]: monaco.languages.CompletionItemKind.Function,
    [LspCompletionItemKind.Constructor]: monaco.languages.CompletionItemKind.Constructor,
    [LspCompletionItemKind.Field]: monaco.languages.CompletionItemKind.Field,
    [LspCompletionItemKind.Variable]: monaco.languages.CompletionItemKind.Variable,
    [LspCompletionItemKind.Class]: monaco.languages.CompletionItemKind.Class,
    [LspCompletionItemKind.Interface]: monaco.languages.CompletionItemKind.Interface,
    [LspCompletionItemKind.Module]: monaco.languages.CompletionItemKind.Module,
    [LspCompletionItemKind.Property]: monaco.languages.CompletionItemKind.Property,
    [LspCompletionItemKind.Unit]: monaco.languages.CompletionItemKind.Unit,
    [LspCompletionItemKind.Value]: monaco.languages.CompletionItemKind.Value,
    [LspCompletionItemKind.Enum]: monaco.languages.CompletionItemKind.Enum,
    [LspCompletionItemKind.Keyword]: monaco.languages.CompletionItemKind.Keyword,
    [LspCompletionItemKind.Snippet]: monaco.languages.CompletionItemKind.Snippet,
    [LspCompletionItemKind.Color]: monaco.languages.CompletionItemKind.Color,
    [LspCompletionItemKind.File]: monaco.languages.CompletionItemKind.File,
    [LspCompletionItemKind.Reference]: monaco.languages.CompletionItemKind.Reference,
    [LspCompletionItemKind.Folder]: monaco.languages.CompletionItemKind.Folder,
    [LspCompletionItemKind.EnumMember]: monaco.languages.CompletionItemKind.EnumMember,
    [LspCompletionItemKind.Constant]: monaco.languages.CompletionItemKind.Constant,
    [LspCompletionItemKind.Struct]: monaco.languages.CompletionItemKind.Struct,
    [LspCompletionItemKind.Event]: monaco.languages.CompletionItemKind.Event,
    [LspCompletionItemKind.Operator]: monaco.languages.CompletionItemKind.Operator,
    [LspCompletionItemKind.TypeParameter]: monaco.languages.CompletionItemKind.TypeParameter
};

function mapDocumentation(
    doc: LspCompletionItem['documentation']
): string | monaco.IMarkdownString | undefined {
    if (!doc) return undefined;
    if (typeof doc === 'string') return doc;
    return { value: (doc as MarkupContent).value };
}

function enrichWithSchemaDocs(
    item: monaco.languages.CompletionItem
): monaco.languages.CompletionItem {
    if (item.documentation) return item;
    const label = typeof item.label === 'string' ? item.label : item.label.label;

    const receiver = findReceiverByName(label);
    if (receiver) {
        return {
            ...item,
            detail: receiver.description,
            documentation: { value: receiver.description }
        };
    }
    for (const r of RECEIVERS) {
        const field = findFieldByName(r, label);
        if (field) {
            return {
                ...item,
                detail: `(field) ${r.name}.${field.name}: ${field.type}`,
                documentation: { value: field.description }
            };
        }
    }
    return item;
}

function lspToMonacoCompletion(
    item: LspCompletionItem,
    fallbackRange: monaco.IRange
): monaco.languages.CompletionItem {
    const isSnippet = item.insertTextFormat === LspInsertTextFormat.Snippet;

    let range: monaco.IRange = fallbackRange;
    let insertText = item.insertText ?? item.label;
    if (item.textEdit && 'range' in item.textEdit) {
        const r = item.textEdit.range;
        range = {
            startLineNumber: r.start.line + 1,
            startColumn: r.start.character + 1,
            endLineNumber: r.end.line + 1,
            endColumn: r.end.character + 1
        };
        insertText = item.textEdit.newText;
    }

    return enrichWithSchemaDocs({
        label: item.label,
        kind: item.kind
            ? (LSP_TO_MONACO_KIND[item.kind] ?? monaco.languages.CompletionItemKind.Text)
            : monaco.languages.CompletionItemKind.Text,
        detail: item.detail,
        documentation: mapDocumentation(item.documentation),
        insertText,
        insertTextRules: isSnippet
            ? monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet
            : undefined,
        range,
        sortText: item.sortText,
        filterText: item.filterText
    });
}

async function getCompletions(
    model: monaco.editor.ITextModel,
    position: monaco.Position
): Promise<monaco.languages.CompletionList> {
    const services = getServices();
    const provider = services.LightlyQuery.lsp.CompletionProvider;
    if (!provider) return { suggestions: [] };

    const doc = await syncDocument(model);

    const word = model.getWordUntilPosition(position);
    const fallbackRange: monaco.IRange = {
        startLineNumber: position.lineNumber,
        endLineNumber: position.lineNumber,
        startColumn: word.startColumn,
        endColumn: word.endColumn
    };

    const result: LspCompletionList | undefined = await provider.getCompletion(doc, {
        textDocument: { uri: doc.uri.toString() },
        position: { line: position.lineNumber - 1, character: position.column - 1 }
    });

    return {
        suggestions: (result?.items ?? []).map((item) => lspToMonacoCompletion(item, fallbackRange))
    };
}

function getHover(
    model: monaco.editor.ITextModel,
    position: monaco.Position
): monaco.languages.Hover | null {
    const word = model.getWordAtPosition(position);
    if (!word) return null;

    const line = model.getLineContent(position.lineNumber);
    const cursorOffset = position.column - 1;

    const qualifiedReference = /([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)/g;
    let match: RegExpExecArray | null;
    while ((match = qualifiedReference.exec(line))) {
        const fullStart = match.index;
        const fullEnd = match.index + match[0].length;
        if (cursorOffset < fullStart || cursorOffset > fullEnd) continue;

        const receiver = findReceiverByName(match[1]);
        if (!receiver) continue;

        const memberStart = match.index + match[1].length + 1;
        if (cursorOffset >= memberStart) {
            const field = findFieldByName(receiver, match[2]);
            if (!field) return null;
            return {
                contents: [
                    { value: `\`\`\`\n${receiver.name}.${field.name}: ${field.type}\n\`\`\`` },
                    { value: field.description }
                ],
                range: new monaco.Range(
                    position.lineNumber,
                    memberStart + 1,
                    position.lineNumber,
                    memberStart + 1 + match[2].length
                )
            };
        }
        return {
            contents: [{ value: `**${receiver.name}** — ${receiver.description}` }],
            range: new monaco.Range(
                position.lineNumber,
                fullStart + 1,
                position.lineNumber,
                fullStart + 1 + match[1].length
            )
        };
    }

    const receiver = findReceiverByName(word.word);
    if (receiver) {
        return {
            contents: [{ value: `**${receiver.name}** — ${receiver.description}` }],
            range: new monaco.Range(
                position.lineNumber,
                word.startColumn,
                position.lineNumber,
                word.endColumn
            )
        };
    }
    return null;
}

let providersRegistered = false;
function registerProviders(): void {
    if (providersRegistered) return;
    providersRegistered = true;

    monaco.languages.registerCompletionItemProvider(LANGUAGE_ID, {
        triggerCharacters: ['.', ' ', '('],
        provideCompletionItems: (model, position) => getCompletions(model, position)
    });

    monaco.languages.registerHoverProvider(LANGUAGE_ID, {
        provideHover: (model, position) => getHover(model, position)
    });
}

export interface UseLightlyQueryLanguageReturn {
    attach: (model: monaco.editor.ITextModel) => () => void;
    translateQuery: (value: string) => QueryExprTranslationResult;
}

export function useLightlyQueryLanguage(): UseLightlyQueryLanguageReturn {
    const services = getServices();
    const parser = services.LightlyQuery.parser.LangiumParser;

    function validate(model: monaco.editor.ITextModel): void {
        const result = parser.parse(model.getValue());
        const markers = [
            ...result.lexerErrors.map((e) => lexerErrorToMarker(e as LexerErrorLike)),
            ...result.parserErrors.map((e) => parserErrorToMarker(e as ParserErrorLike))
        ];
        monaco.editor.setModelMarkers(model, MARKER_OWNER, markers);
    }

    function attach(model: monaco.editor.ITextModel): () => void {
        registerProviders();
        validate(model);
        const sub = model.onDidChangeContent(() => validate(model));
        return () => {
            sub.dispose();
            monaco.editor.setModelMarkers(model, MARKER_OWNER, []);
        };
    }

    function translateQuery(value: string): QueryExprTranslationResult {
        return parseLightlyQuery(parser, value);
    }

    return { attach, translateQuery };
}
