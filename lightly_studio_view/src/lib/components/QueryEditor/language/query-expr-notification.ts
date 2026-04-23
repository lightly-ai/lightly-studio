// Shared contract for the custom LSP notification that carries the parsed
// QueryExpr from the Langium worker to the main thread. Both sides import
// this module so the notification method string and payload shape stay in sync.

import { NotificationType } from 'vscode-languageserver-protocol';
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
