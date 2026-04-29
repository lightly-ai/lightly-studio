/** Main-thread Langium integration for the LightlyQuery editor.
 *
 * The Langium parser runs directly on the main thread (no worker, no LSP).
 * Diagnostics are pushed into Monaco via `setModelMarkers`, and `translateQuery`
 * is a synchronous call into `parseLightlyQuery`. */

import * as monaco from 'monaco-editor';
import {
    createLightlyQueryServices,
    type LightlyQueryServicesBundle
} from './language/lightly-query-module';
import {
    parseLightlyQuery,
    type QueryExprTranslationResult
} from './language/query-expr-translation';

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
    // Chevrotain's endColumn is the column of the last character; Monaco's
    // endColumn is exclusive, so add 1.
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
