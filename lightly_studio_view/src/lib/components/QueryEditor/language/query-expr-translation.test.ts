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
import type { Query } from './generated/ast.js';

function createParser() {
    const shared = inject(
        createDefaultSharedCoreModule(EmptyFileSystem),
        LightlyQueryGeneratedSharedModule
    );
    const LightlyQuery = inject(createDefaultCoreModule({ shared }), LightlyQueryGeneratedModule);
    shared.ServiceRegistry.register(LightlyQuery);
    return LightlyQuery.parser.LangiumParser;
}

describe('QueryExprTranslationRequest', () => {
    it('has the expected method name', () => {
        expect(QueryExprTranslationRequest.method).toBe('lightly-query/queryExprTranslation');
    });
});

describe('parseLightlyQuery', () => {
    it('example parse-translate test', () => {
        const parser = createParser();

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
