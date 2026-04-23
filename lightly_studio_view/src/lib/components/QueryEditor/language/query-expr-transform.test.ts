import { parseQuery, toQueryExpr, QueryParseError } from './query-expr-transform';

describe('parseQuery', () => {
    test('parses a valid query string into a Query AST', () => {
        const query = parseQuery('ImageSampleField.width > 100');
        expect(query.$type).toBe('Query');
    });

    test('throws QueryParseError on invalid input', () => {
        expect(() => parseQuery('AND AND AND')).toThrow(QueryParseError);
    });
});

describe('toQueryExpr', () => {
    test('dummy implementation returns object_detection(label=="cat")', () => {
        const query = parseQuery('ImageSampleField.width > 100');
        const result = toQueryExpr(query);
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
