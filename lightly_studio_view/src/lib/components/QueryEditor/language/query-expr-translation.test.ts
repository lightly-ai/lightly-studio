import { describe, it, expect } from 'vitest';
import { QueryExprTranslationRequest, toQueryExpr } from './query-expr-translation.js';
import type { Query } from './generated/ast.js';

describe('QueryExprTranslationRequest', () => {
    it('has the expected method name', () => {
        expect(QueryExprTranslationRequest.method).toBe('lightly-query/queryExprTranslation');
    });
});

describe('toQueryExpr', () => {
    it('returns an error result when the parser reports errors', () => {
        const result = toQueryExpr({
            lexerErrors: [],
            parserErrors: [{ message: 'Unexpected token', line: 3, column: 5 }],
            value: {} as Query
        });

        expect(result).toEqual({
            status: 'error',
            errors: [{ message: 'Unexpected token', line: 3, column: 5 }]
        });
    });

    it('returns the hardcoded object_detection stub when parsing succeeds', () => {
        const result = toQueryExpr({
            lexerErrors: [],
            parserErrors: [],
            value: {} as Query
        });

        expect(result).toEqual({
            status: 'ok',
            queryExpr: {
                match_expr: {
                    type: 'object_detection_match_expr',
                    subexpr: {
                        type: 'string_expr',
                        field: { table: 'object_detection', name: 'label' },
                        operator: '==',
                        value: 'cat'
                    }
                }
            }
        });
    });
});
