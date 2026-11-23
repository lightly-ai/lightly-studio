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
import { findUnknownTagMarkers } from './findUnknownTagMarkers';
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
     * backend `QueryExpr` (`status: 'ok'`), no expression (`status: 'empty'`), or lexer/parser errors
     * (`status: 'error'`). Intended for one-off translation outside the editor
     * lifecycle (e.g. on Save). */
    translateQuery: (value: string, sampleType?: 'image' | 'video') => QueryExprTranslationResult;
    /** Sets the tag names that exist in the collection and re-validates the
     * attached models. Pass `undefined` while the names are unknown to skip
     * the tag check. */
    setTagNames: (names: string[] | undefined) => void;
}

export function useLightlyQueryLanguage(): UseLightlyQueryLanguageReturn {
    const services = getServices();
    const parser = services.LightlyQuery.parser.LangiumParser;
    const attachedModels = new Set<monaco.editor.ITextModel>();
    let tagNames: ReadonlySet<string> | undefined;

    function validate(model: monaco.editor.ITextModel): void {
        const { text, lineOffset } = getModelQuerySource(model);
        const result = parser.parse<Query>(text);
        const errorMarkers = [
            ...result.lexerErrors.map((e) => lexerErrorToMarker(e as LexerErrorLike)),
            ...result.parserErrors.map((e) => parserErrorToMarker(e as ParserErrorLike))
        ].map((marker) => shiftMarkerLines(marker, lineOffset));
        const scopeError = getQueryScopeError(result.value, modelSampleTypes.get(model));
        if (errorMarkers.length === 0 && scopeError) {
            const start = result.value.$cstNode?.range.start;
            errorMarkers.push(
                parserErrorToMarker({
                    message: scopeError,
                    token: {
                        startLine: (start?.line ?? 0) + 1,
                        startColumn: (start?.character ?? 0) + 1
                    }
                })
            );
        }
        // Tag warnings come after the scope check so that they do not hide a scope error.
        // TODO(Nauryzbay, 11/2026): Also warn about other names that may not exist, such as
        // annotation `class_name` values and sample evaluation names.
        const tagMarkers = tagNames
            ? findUnknownTagMarkers({ query: result.value, tagNames }).map((marker) =>
                  shiftMarkerLines(marker, lineOffset)
              )
            : [];
        monaco.editor.setModelMarkers(model, MARKER_OWNER, [...errorMarkers, ...tagMarkers]);
    }

    function attach(model: monaco.editor.ITextModel, sampleType?: 'image' | 'video'): () => void {
        if (sampleType) modelSampleTypes.set(model, sampleType);
        attachedModels.add(model);
        validate(model);
        const sub = model.onDidChangeContent(() => validate(model));
        return () => {
            sub.dispose();
            modelSampleTypes.delete(model);
            attachedModels.delete(model);
            monaco.editor.setModelMarkers(model, MARKER_OWNER, []);
        };
    }

    function translateQuery(
        value: string,
        sampleType?: 'image' | 'video'
    ): QueryExprTranslationResult {
        return parseLightlyQuery(parser, value, sampleType);
    }

    function setTagNames(names: string[] | undefined): void {
        tagNames = names && new Set(names);
        attachedModels.forEach(validate);
    }

    return { attach, translateQuery, setTagNames };
}

/** Moves a marker up by the lines of the hidden scope prefix, so it lands on the visible query. */
function shiftMarkerLines(
    marker: monaco.editor.IMarkerData,
    lineOffset: number
): monaco.editor.IMarkerData {
    return {
        ...marker,
        startLineNumber: Math.max(1, marker.startLineNumber - lineOffset),
        endLineNumber: Math.max(1, marker.endLineNumber - lineOffset)
    };
}
