// Shared contract for the custom LSP messages that carry the parsed QueryExpr
// between the Langium worker and the main thread. Both sides import this
// module so the method strings and payload shapes stay in sync.

import { NotificationType, RequestType } from 'vscode-languageserver-protocol';
import type { QueryExpr } from '$lib/api/lightly_studio_local';
import type { Query } from './generated/ast.js';

export interface QueryParseError {
    message: string;
    line?: number;
    column?: number;
}

export type QueryExprNotificationParams =
    | { status: 'ok'; queryExpr: QueryExpr }
    | { status: 'error'; errors: QueryParseError[] };

export const QueryExprNotification = new NotificationType<QueryExprNotificationParams>(
    'lightly-query/queryExpr'
);

export const GetLatestQueryExprRequest = new RequestType<
    void,
    QueryExprNotificationParams | null,
    never
>('lightly-query/getLatestQueryExpr');

export function toQueryExprNotificationParams(parseResult: {
    lexerErrors: Array<{ message: string; line?: number; column?: number }>;
    parserErrors: Array<{ message: string; line?: number; column?: number }>;
    value: Query;
}): QueryExprNotificationParams {
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
