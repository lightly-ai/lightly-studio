import { describe, it, expect } from 'vitest';
import {
    EmptyFileSystem,
    createDefaultCoreModule,
    createDefaultSharedCoreModule,
    inject
} from 'langium';
import { QueryExprTranslationRequest, parseLightlyQuery } from './query-expr-translation.js';
import {
    LightlyQueryGeneratedModule,
    LightlyQueryGeneratedSharedModule
} from './generated/module.js';

function createParser() {
    const shared = inject(
        createDefaultSharedCoreModule(EmptyFileSystem),
        LightlyQueryGeneratedSharedModule
    );
    const lightlyQuery = inject(createDefaultCoreModule({ shared }), LightlyQueryGeneratedModule);
    shared.ServiceRegistry.register(lightlyQuery);
    return lightlyQuery.parser.LangiumParser;
}

const parser = createParser();

describe('QueryExprTranslationRequest', () => {
    it('has the expected method name', () => {
        expect(QueryExprTranslationRequest.method).toBe('lightly-query/queryExprTranslation');
    });
});

describe('parseLightlyQuery error handling', () => {
    it('returns an error result when the parser reports errors', () => {
        const result = parseLightlyQuery(parser, 'invalid_query');

        expect(result.status).toBe('error');
        if (result.status !== 'error') return;
        expect(result.errors).toHaveLength(2);
        expect(result.errors[0].message).toMatch(/unexpected character/);
        expect(result.errors[1].message).toMatch(
            /Expecting: one of these possible Token sequences:/
        );
    });
});

describe('parseLightlyQuery', () => {
    it('example parse-translate test', () => {
        const result = parseLightlyQuery(parser, 'Image.width == 1000');

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
