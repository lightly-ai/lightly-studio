import { describe, it, expect } from 'vitest';
import { QueryExprNotification, toQueryExpr } from './query-expr-notification.js';
import type { Query } from './generated/ast.js';

describe('QueryExprNotification', () => {
    it('has the expected method name', () => {
        expect(QueryExprNotification.method).toBe('lightly-query/queryExpr');
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
