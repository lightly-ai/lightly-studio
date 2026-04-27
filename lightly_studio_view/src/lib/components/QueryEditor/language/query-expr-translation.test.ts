import { describe, it, expect } from 'vitest';
import { QueryExprTranslationRequest, parseLightlyQuery } from './query-expr-translation.js';
import type { Query } from './generated/ast.js';

describe('QueryExprTranslationRequest', () => {
    it('has the expected method name', () => {
        expect(QueryExprTranslationRequest.method).toBe('lightly-query/queryExprTranslation');
    });
});

describe('parseLightlyQuery', () => {
    it('returns an error result when the parser reports errors', () => {
        const result = parseLightlyQuery(
            {
                parse: () => ({
                    lexerErrors: [],
                    parserErrors: [{ message: 'Unexpected token', line: 3, column: 5 }],
                    value: {} as Query
                })
            },
            'invalid'
        );

        expect(result).toEqual({
            status: 'error',
            errors: [{ message: 'Unexpected token', line: 3, column: 5 }]
        });
    });

    it('returns the hardcoded query stub when parsing succeeds', () => {
        const result = parseLightlyQuery(
            {
                parse: () => ({
                    lexerErrors: [],
                    parserErrors: [],
                    value: {} as Query
                })
            },
            'valid'
        );

        expect(result).toEqual({
            status: 'ok',
            queryExpr: {
                match_expr: {
                    type: 'integer_expr',
                    field: { table: 'image', name: 'width' },
                    operator: '<',
                    value: 400
                }
            }
        });
    });
});
