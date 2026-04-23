import { describe, it, expect } from 'vitest';
import {
    TranslateQueryExprRequest,
    toQueryExpr,
    toQueryExprTranslationResult
} from './query-expr-translation.js';
import type { Query } from './generated/ast.js';

describe('TranslateQueryExprRequest', () => {
    it('has the expected method name', () => {
        expect(TranslateQueryExprRequest.method).toBe('lightly-query/translateQueryExpr');
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

describe('toQueryExprTranslationResult', () => {
    it('returns an error result when the parser reports errors', () => {
        const result = toQueryExprTranslationResult({
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
