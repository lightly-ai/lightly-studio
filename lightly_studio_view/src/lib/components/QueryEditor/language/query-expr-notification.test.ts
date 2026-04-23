import { describe, it, expect } from 'vitest';
import {
    GetLatestQueryExprRequest,
    QueryExprNotification,
    toQueryExpr,
    toQueryExprNotificationParams
} from './query-expr-notification.js';
import type { Query } from './generated/ast.js';

describe('QueryExprNotification', () => {
    it('has the expected method name', () => {
        expect(QueryExprNotification.method).toBe('lightly-query/queryExpr');
    });
});

describe('GetLatestQueryExprRequest', () => {
    it('has the expected method name', () => {
        expect(GetLatestQueryExprRequest.method).toBe('lightly-query/getLatestQueryExpr');
    });
});

describe('toQueryExpr', () => {
    it('returns the hardcoded object_detection stub', () => {
        const result = toQueryExpr({} as Query);

        expect(result).toEqual({
            match_expr: {
                type: 'object_detection_match_expr',
                subexpr: {
                    type: 'string_expr',
                    field: { table: 'object_detection', name: 'label' },
                    operator: '==',
                    value: 'cat'
                }
            }
        });
    });
});

describe('toQueryExprNotificationParams', () => {
    it('returns error params when the parser reports errors', () => {
        const result = toQueryExprNotificationParams({
            lexerErrors: [],
            parserErrors: [{ message: 'Unexpected token', line: 3, column: 5 }],
            value: {} as Query
        });

        expect(result).toEqual({
            status: 'error',
            errors: [{ message: 'Unexpected token', line: 3, column: 5 }]
        });
    });
});
