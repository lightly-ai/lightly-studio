/** Main-thread Langium integration for the LightlyQuery editor.
 *
 * The Langium parser runs directly on the main thread (no worker, no LSP).
 * Diagnostics are pushed into Monaco via `setModelMarkers`, and `translateQuery`
 * is a synchronous call into `parseLightlyQuery`. */

import * as monaco from 'monaco-editor';
import type { Query } from '../language/generated/ast';
import { getQueryScopeError } from '../language/getQueryScopeError';
import {
    createLightlyQueryServices,
    type LightlyQueryServicesBundle
} from '../language/lightly-query-module';
import {
    parseLightlyQuery,
    type QueryExprTranslationResult
} from '../language/query-expr-translation';
import { lexerErrorToMarker, type LexerErrorLike } from './lexerErrorToMarker';
import { parserErrorToMarker, type ParserErrorLike } from './parserErrorToMarker';
import { getModelQuerySource, modelSampleTypes } from './modelQueryScope';

const LANGUAGE_ID = 'lightly-query';
const MARKER_OWNER = LANGUAGE_ID;

// Lazy module-level singleton for the Langium DI container. The hook is
// called on every editor mount, but we only want to build the parser/services
// once: composition is expensive, and `createLightlyQueryServices` registers
// the language in a shared `ServiceRegistry` that misbehaves on duplicate
// registration. Lazy (vs. a top-level const) so importers that never mount
// the editor don't pay the init cost.
let cachedServices: LightlyQueryServicesBundle | null = null;
function getServices(): LightlyQueryServicesBundle {
    if (!cachedServices) {
        cachedServices = createLightlyQueryServices();
    }
    return cachedServices;
}

export interface UseLightlyQueryLanguageReturn {
    /** Wires the language service to a Monaco model: runs an initial validation
     * pass, subscribes to content changes to keep diagnostics in sync, and
     * publishes errors as Monaco markers. Returns a cleanup function that
     * disposes the subscription and clears any markers this hook owns. */
    attach: (model: monaco.editor.ITextModel, sampleType?: 'image' | 'video') => () => void;
    /** Synchronously parses a query string and returns either the translated
     * backend `QueryExpr` (`status: 'ok'`) or the collected lexer/parser errors
     * (`status: 'error'`). Intended for one-off translation outside the editor
     * lifecycle (e.g. on Save). */
    translateQuery: (value: string, sampleType?: 'image' | 'video') => QueryExprTranslationResult;
}

export function useLightlyQueryLanguage(): UseLightlyQueryLanguageReturn {
    const services = getServices();
    const parser = services.LightlyQuery.parser.LangiumParser;

    function validate(model: monaco.editor.ITextModel): void {
        const { text, lineOffset } = getModelQuerySource(model);
        const result = parser.parse<Query>(text);
        const markers = [
            ...result.lexerErrors.map((e) => lexerErrorToMarker(e as LexerErrorLike)),
            ...result.parserErrors.map((e) => parserErrorToMarker(e as ParserErrorLike))
        ].map((marker) => ({
            ...marker,
            startLineNumber: Math.max(1, marker.startLineNumber - lineOffset),
            endLineNumber: Math.max(1, marker.endLineNumber - lineOffset)
        }));
        const scopeError = getQueryScopeError(result.value, modelSampleTypes.get(model));
        if (markers.length === 0 && scopeError) {
            const start = result.value.$cstNode?.range.start;
            markers.push(
                parserErrorToMarker({
                    message: scopeError,
                    token: {
                        startLine: (start?.line ?? 0) + 1,
                        startColumn: (start?.character ?? 0) + 1
                    }
                })
            );
        }
        monaco.editor.setModelMarkers(model, MARKER_OWNER, markers);
    }

    function attach(model: monaco.editor.ITextModel, sampleType?: 'image' | 'video'): () => void {
        if (sampleType) modelSampleTypes.set(model, sampleType);
        validate(model);
        const sub = model.onDidChangeContent(() => validate(model));
        return () => {
            sub.dispose();
            modelSampleTypes.delete(model);
            monaco.editor.setModelMarkers(model, MARKER_OWNER, []);
        };
    }

    function translateQuery(
        value: string,
        sampleType?: 'image' | 'video'
    ): QueryExprTranslationResult {
        return parseLightlyQuery(parser, value, sampleType);
    }

    return { attach, translateQuery };
}
