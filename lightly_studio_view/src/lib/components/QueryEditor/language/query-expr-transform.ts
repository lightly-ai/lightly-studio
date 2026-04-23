/**
 * Transforms a Langium-parsed Query AST into a QueryExpr object
 * compatible with the backend API.
 */

import type { LangiumParser } from 'langium';
import type { Query } from './generated/ast';
import type { QueryExpr } from '$lib/api/lightly_studio_local';
import { createLightlyQueryCoreServices } from './lightly-query-module.js';

let _parser: LangiumParser | undefined;

function getParser(): LangiumParser {
    if (!_parser) {
        const services = createLightlyQueryCoreServices();
        _parser = services.parser.LangiumParser;
    }
    return _parser;
}

export class QueryParseError extends Error {
    constructor(message: string) {
        super(message);
        this.name = 'QueryParseError';
    }
}

/**
 * Parses a query string into a Langium Query AST.
 *
 * @throws {QueryParseError} if the input has lexer or parser errors.
 */
export function parseQuery(input: string): Query {
    const result = getParser().parse<Query>(input);
    const errors: string[] = [
        ...result.lexerErrors.map((e) => e.message),
        ...result.parserErrors.map((e) => e.message)
    ];
    if (errors.length > 0) {
        throw new QueryParseError(errors.join('\n'));
    }
    return result.value;
}

/**
 * TODO(Michal, 04/2026): Implement full recursive visitor over the Langium AST.
 * Currently returns a hardcoded `object_detection(label=="cat")` query.
 */
export function toQueryExpr(_query: Query): QueryExpr {
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
