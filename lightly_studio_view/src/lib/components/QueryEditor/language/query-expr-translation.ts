// Shared contract for translating a parsed query into the backend QueryExpr.
// Both sides import this module so the request method and result shape stay
// in sync.

import { RequestType } from 'vscode-languageserver-protocol';
import type { QueryExpr } from '$lib/api/lightly_studio_local';
import type { Query } from './generated/ast.js';

export interface QueryParseError {
    message: string;
    line?: number;
    column?: number;
}

export type QueryExprTranslationResult =
    | { status: 'ok'; queryExpr: QueryExpr }
    | { status: 'error'; errors: QueryParseError[] };

export const TranslateQueryExprRequest = new RequestType<
    void,
    QueryExprTranslationResult | null,
    never
>('lightly-query/translateQueryExpr');

export function toQueryExprTranslationResult(parseResult: {
    lexerErrors: Array<{ message: string; line?: number; column?: number }>;
    parserErrors: Array<{ message: string; line?: number; column?: number }>;
    value: Query;
}): QueryExprTranslationResult {
    const errors = [...parseResult.lexerErrors, ...parseResult.parserErrors];
    if (errors.length > 0) {
        return {
            status: 'error',
            errors: errors.map((error) => ({
                message: error.message,
                line: error.line,
                column: error.column
            }))
        };
    }

    return {
        status: 'ok',
        queryExpr: toQueryExpr(parseResult.value)
    };
}

/**
 * Converts a Langium parse result into a backend-compatible QueryExpr.
 *
 * Stub: always returns `object_detection(label == "cat")`. The real recursive
 * AST visitor will replace this once the grammar-to-API mapping is finalized.
 */
export function toQueryExpr(_parseResult: Query): QueryExpr {
    return {
        match_expr: {
            type: 'object_detection_match_expr',
            subexpr: {
                type: 'string_expr',
                field: { table: 'object_detection', name: 'label' },
                operator: '==',
                value: 'cat'
            }
        }
    };
}
