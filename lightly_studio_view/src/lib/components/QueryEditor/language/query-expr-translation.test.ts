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

    it('returns the hardcoded object_detection stub when parsing succeeds', () => {
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

    it('returns the hardcoded object_detection stub for a valid object_detection query', () => {
        const result = parseLightlyQuery(
            {
                parse: () => ({
                    lexerErrors: [],
                    parserErrors: [],
                    value: {} as Query
                })
            },
            'object_detection(label == "cat")'
        );

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
