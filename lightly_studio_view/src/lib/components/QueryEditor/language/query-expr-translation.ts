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

export const QueryExprTranslationRequest = new RequestType<
    string,
    QueryExprTranslationResult | null,
    never
>('lightly-query/queryExprTranslation');

interface TranslationParser {
    parse: (value: string) => {
        lexerErrors: Array<{ message: string; line?: number; column?: number }>;
        parserErrors: Array<{ message: string; line?: number; column?: number }>;
        value: Query;
    };
}

export function parseLightlyQuery(
    parser: TranslationParser,
    value: string
): QueryExprTranslationResult {
    const parseResult = parser.parse(value);
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
 * Converts a Langium AST into a backend-compatible QueryExpr.
 *
 * Stub: always returns `object_detection(label == "cat")`. The real recursive
 * AST visitor will replace this once the grammar-to-API mapping is finalized.
 */
function toQueryExpr(_parseResult: Query): QueryExpr {
    return {
        match_expr: {
            type: ''
            subexpr: {
                type: 'integer_expr',
                field: { table: 'image', name: 'width' },
                operator: '>',
                value: 600
            }
        }
    };
}
