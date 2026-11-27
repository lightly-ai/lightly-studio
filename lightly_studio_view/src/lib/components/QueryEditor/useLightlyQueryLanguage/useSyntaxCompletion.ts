/** Module to attach Monaco syntax completion */
import * as monaco from 'monaco-editor';
import { type CompletionList as LspCompletionList } from 'vscode-languageserver-types';
import {
    createLightlyQueryServices,
    type LightlyQueryServicesBundle
} from '../language/lightly-query-module';
import { detectScopeAt } from '../language/lightly-query-schema';
import { getMetadataQueryContext } from '$lib/components/QueryEditor/language';
import { getEvaluationCompletionContext } from './getEvaluationCompletionContext';
import { getModelQuerySource } from './modelQueryScope';
import { getQuotedMetricRange } from './getQuotedMetricRange';
import {
    buildSchemaCompletions,
    lspToMonacoCompletion,
    syncLangiumDocument
} from './completionAdapter';

let cachedServices: LightlyQueryServicesBundle | null = null;
const registeredCompletionLanguages = new Set<string>();
function getServices(): LightlyQueryServicesBundle {
    if (!cachedServices) {
        cachedServices = createLightlyQueryServices();
    }
    return cachedServices;
}

function completionLabel(item: monaco.languages.CompletionItem): string {
    return typeof item.label === 'string' ? item.label : item.label.label;
}

// Keep parsing support for leading `video:` queries, but do not advertise the
// prefix in autocomplete for now. Filtering here ensures it is removed no
// matter whether it comes from Langium's LSP completions or our schema fallback.
function shouldShowSuggestion(
    item: monaco.languages.CompletionItem,
    metadataContext: ReturnType<typeof getMetadataQueryContext>
): boolean {
    const label = completionLabel(item);
    if (label === 'metadata') return metadataContext === 'field';
    if (label === 'true' || label === 'false') return metadataContext === 'boolean';
    return label !== 'video:';
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

    const { text, lineOffset } = getModelQuerySource(model);
    const doc = await syncLangiumDocument(model, services, text);

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
        // Monaco positions are 1-based; LSP expects 0-based line/character.
        position: { line: lineNumber - 1 + lineOffset, character: column - 1 }
    });

    const scope = detectScopeAt(
        text,
        model.getOffsetAt(position) + text.length - model.getValue().length
    );

    const metadataContext = getMetadataQueryContext({
        text: model.getValue(),
        offset: model.getOffsetAt(position) - (position.column - word.startColumn)
    });
    const evaluationContext =
        scope === 'sample_evaluation'
            ? getEvaluationCompletionContext({
                  text: model.getValue(),
                  offset: model.getOffsetAt(position)
              })
            : undefined;
    const isSupported = (item: monaco.languages.CompletionItem) => {
        const label = completionLabel(item);
        if (evaluationContext === 'selector') {
            if (label.startsWith('"') || ['AND', 'OR', 'NOT'].includes(label)) return false;
        }
        if (evaluationContext === 'run' && label.startsWith('"')) return false;
        if (evaluationContext && evaluationContext !== 'selector' && label === 'name') return false;
        return shouldShowSuggestion(item, metadataContext);
    };
    const lspSuggestions = (result?.items ?? [])
        .map((item) => lspToMonacoCompletion(item, fallbackRange, scope, lineOffset))
        // Use the schema snippet instead of Langium's bare metadata keyword.
        .filter((item) => completionLabel(item) !== 'metadata')
        .filter(isSupported);

    // Langium's default provider only emits literal-string keywords from the
    // grammar, so terminal-defined names (width, fps, object_detection, …)
    // never show up. Augment with scope-aware schema completions and dedupe
    // against the LSP results.
    const seen = new Set(lspSuggestions.map(completionLabel));
    const schemaSuggestions = buildSchemaCompletions({
        scope,
        range: fallbackRange,
        includeBooleanLiterals: metadataContext === 'boolean'
    }).filter((suggestion) => !seen.has(completionLabel(suggestion)));

    const metricRange =
        scope === 'sample_evaluation'
            ? getQuotedMetricRange({
                  text: model.getValue(),
                  offset: model.getOffsetAt(position),
                  position
              })
            : undefined;
    const metricQuote = metricRange
        ? model.getValue()[model.getOffsetAt(position) - column + metricRange.startColumn]
        : undefined;
    return {
        suggestions: [...lspSuggestions, ...schemaSuggestions].filter(isSupported).map((item) =>
            metricRange && completionLabel(item).startsWith('"')
                ? {
                      ...item,
                      range: metricRange,
                      filterText: `${metricQuote}${completionLabel(item).slice(1, -1)}${metricQuote}`
                  }
                : item
        )
    };
}

/**
 * Hook to attach syntax completion
 */
export function useSyntaxCompletion(params: { languageId: string }) {
    const { languageId } = params;
    if (registeredCompletionLanguages.has(languageId)) return;
    monaco.languages.registerCompletionItemProvider(languageId, {
        triggerCharacters: [' ', '(', ':'],
        provideCompletionItems: (model, position) => getCompletions(model, position)
    });
    registeredCompletionLanguages.add(languageId);
}
