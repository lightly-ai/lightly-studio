/** Module to attach Monaco syntax completion */
import * as monaco from 'monaco-editor';
import { type CompletionList as LspCompletionList } from 'vscode-languageserver-types';
import {
    createLightlyQueryServices,
    type LightlyQueryServicesBundle
} from '../language/lightly-query-module';
import { detectScopeAt } from '../language/lightly-query-schema';
import {
    buildSchemaCompletions,
    lspToMonacoCompletion,
    syncLangiumDocument
} from './completionAdapter';

let cachedServices: LightlyQueryServicesBundle | null = null;
function getServices(): LightlyQueryServicesBundle {
    if (!cachedServices) {
        cachedServices = createLightlyQueryServices();
    }
    return cachedServices;
}

function completionLabel(item: monaco.languages.CompletionItem): string {
    return typeof item.label === 'string' ? item.label : item.label.label;
}

async function getCompletions(
    model: monaco.editor.ITextModel,
    position: monaco.Position
): Promise<monaco.languages.CompletionList> {
    const services = getServices();
    const {
        LightlyQuery: {
            lsp: { CompletionProvider: provider }
        }
    } = services;
    if (!provider) return { suggestions: [] };

    const doc = await syncLangiumDocument(model, services);

    const word = model.getWordUntilPosition(position);
    const { lineNumber, column } = position;
    const fallbackRange: monaco.IRange = {
        startLineNumber: lineNumber,
        endLineNumber: lineNumber,
        startColumn: word.startColumn,
        endColumn: word.endColumn
    };

    const result: LspCompletionList | undefined = await provider.getCompletion(doc, {
        textDocument: { uri: doc.uri.toString() },
        position: { line: lineNumber - 1, character: column - 1 }
    });

    const scope = detectScopeAt(model.getValue(), model.getOffsetAt(position));

    const lspSuggestions = (result?.items ?? []).map((item) =>
        lspToMonacoCompletion(item, fallbackRange, scope)
    );

    // Langium's default provider only emits literal-string keywords from the
    // grammar, so terminal-defined names (width, fps, object_detection, …)
    // never show up. Augment with scope-aware schema completions and dedupe
    // against the LSP results.
    const seen = new Set(lspSuggestions.map(completionLabel));
    const schemaSuggestions = buildSchemaCompletions(scope, fallbackRange).filter(
        (suggestion) => !seen.has(completionLabel(suggestion))
    );

    return { suggestions: [...lspSuggestions, ...schemaSuggestions] };
}

/**
 * Hook to attach syntax completion
 */
export function useSyntaxCompletion(params: { languageId: string }) {
    const { languageId } = params;
    monaco.languages.registerCompletionItemProvider(languageId, {
        triggerCharacters: [' ', '(', ':'],
        provideCompletionItems: (model, position) => getCompletions(model, position)
    });
}
