/** Module to attach Monaco syntax completion */
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
} from '../language/lightly-query-module';
import { type QueryExprTranslationResult } from '../language/query-expr-translation';
import { RECEIVERS, findReceiverByName, findFieldByName } from '../language/lightly-query-schema';

let cachedServices: LightlyQueryServicesBundle | null = null;
function getServices(): LightlyQueryServicesBundle {
    if (!cachedServices) {
        cachedServices = createLightlyQueryServices();
    }
    return cachedServices;
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

export interface UseLightlyQueryLanguageReturn {
    attach: (model: monaco.editor.ITextModel) => () => void;
    translateQuery: (value: string) => QueryExprTranslationResult;
}

/**
 * Hook to attach syntax completion
 */
export function useSyntaxCompletion(params: { languageId: string }) {
    monaco.languages.registerCompletionItemProvider(params.languageId, {
        triggerCharacters: ['.', ' ', '('],
        provideCompletionItems: (model, position) => getCompletions(model, position)
    });
}
