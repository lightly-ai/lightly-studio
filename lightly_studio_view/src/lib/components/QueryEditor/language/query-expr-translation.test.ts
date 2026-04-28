import { describe, it, expect } from 'vitest';
import {
    EmptyFileSystem,
    createDefaultCoreModule,
    createDefaultSharedCoreModule,
    inject
} from 'langium';
import type { LangiumParser } from 'langium';
import { QueryExprTranslationRequest, parseLightlyQuery } from './query-expr-translation.js';
import {
    LightlyQueryGeneratedModule,
    LightlyQueryGeneratedSharedModule
} from './generated/module.js';
import type {
    QueryExpr,
    StringExpr,
    IntegerExpr,
    DatetimeExpr,
    TagsContainsExpr,
    ObjectDetectionMatchExpr,
    AndExpr,
    OrExpr,
    NotExpr
} from '$lib/api/lightly_studio_local';

function createParser(): LangiumParser {
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

/*
 * End-to-end translation tests.
 * Helper functions to construct expected QueryExpr shapes followed by tests cases.
 */

type MatchExpr = QueryExpr['match_expr'];
type OrdOp = IntegerExpr['operator'];
type EqOp = StringExpr['operator'];

const int = (table: string, name: string, operator: OrdOp, value: number): MatchExpr => ({
    type: 'integer_expr',
    field: { table, name },
    operator,
    value
});

const str = (table: string, name: string, operator: EqOp, value: string): MatchExpr => ({
    type: 'string_expr',
    field: { table, name },
    operator,
    value
});

const dt = (table: string, name: string, operator: OrdOp, iso: string): MatchExpr => ({
    type: 'datetime_expr',
    field: { table, name },
    operator,
    value: new Date(iso) as unknown as DatetimeExpr['value']
});

const tagsContains = (table: string, tag: string): MatchExpr =>
    ({
        type: 'tags_contains_expr',
        field: { table, name: 'tags' },
        tag_name: tag
    }) satisfies TagsContainsExpr & { type: 'tags_contains_expr' };

const objectDetection = (subexpr: MatchExpr): MatchExpr =>
    ({
        type: 'object_detection_match_expr',
        subexpr
    }) satisfies ObjectDetectionMatchExpr & { type: 'object_detection_match_expr' };

const and = (...children: MatchExpr[]): MatchExpr =>
    ({
        type: 'and',
        children
    }) satisfies AndExpr & { type: 'and' };

const or = (...children: MatchExpr[]): MatchExpr =>
    ({
        type: 'or',
        children
    }) satisfies OrExpr & { type: 'or' };

const not = (child: MatchExpr): MatchExpr =>
    ({
        type: 'not',
        child
    }) satisfies NotExpr & { type: 'not' };

const query = (match_expr: MatchExpr): QueryExpr => ({ match_expr });

interface TranslationTestCase {
    name: string;
    source: string;
    expected: QueryExpr;
}

const TRANSLATION_TEST_CASES: TranslationTestCase[] = [
    /* Image table fields */
    {
        name: 'image height greater than',
        source: 'height > 400',
        expected: query(int('image', 'height', '>', 400))
    },
    {
        name: 'image width greater than or equal',
        source: 'width >= 640',
        expected: query(int('image', 'width', '>=', 640))
    },
    {
        name: 'image file name equality',
        source: 'file_name == "cat.jpg"',
        expected: query(str('image', 'file_name', '==', 'cat.jpg'))
    },
    {
        name: 'image absolute path inequality',
        source: 'file_path_abs != "/datasets/cats/cat-001.jpg"',
        expected: query(str('image', 'file_path_abs', '!=', '/datasets/cats/cat-001.jpg'))
    },
    {
        name: 'image creation time less than or equal',
        source: 'created_at <= "2026-04-28T12:30:00+02:00"',
        expected: query(dt('image', 'created_at', '<=', '2026-04-28T12:30:00+02:00'))
    },

    /* Tags expression */
    {
        name: 'tag in expression',
        source: '"training" IN tags',
        expected: query(tagsContains('image', 'training'))
    },

    /* Object detection expression */
    {
        name: 'object detection label',
        source: 'object_detection(label == "cat")',
        expected: query(objectDetection(str('object_detection', 'label', '==', 'cat')))
    },
    {
        name: 'object detection x inequality',
        source: 'object_detection(x != 0)',
        expected: query(objectDetection(int('object_detection', 'x', '!=', 0)))
    },
    {
        name: 'object detection y less than',
        source: 'object_detection(y < 200)',
        expected: query(objectDetection(int('object_detection', 'y', '<', 200)))
    },
    {
        name: 'object detection width greater than',
        source: 'object_detection(width > 80)',
        expected: query(objectDetection(int('object_detection', 'width', '>', 80)))
    },
    {
        name: 'object detection height less than or equal',
        source: 'object_detection(height <= 120)',
        expected: query(objectDetection(int('object_detection', 'height', '<=', 120)))
    },

    /* Boolean operators */
    {
        name: 'boolean and',
        source: 'height > 400 AND width >= 640',
        expected: query(and(int('image', 'height', '>', 400), int('image', 'width', '>=', 640)))
    },
    {
        name: 'boolean or',
        source: 'file_name == "cat.jpg" OR file_name == "dog.jpg"',
        expected: query(
            or(
                str('image', 'file_name', '==', 'cat.jpg'),
                str('image', 'file_name', '==', 'dog.jpg')
            )
        )
    },
    {
        name: 'boolean not',
        source: 'NOT "rejected" IN tags',
        expected: query(not(tagsContains('image', 'rejected')))
    },
    {
        name: 'parenthesized precedence',
        source: '(height > 400 OR width > 640) AND "reviewed" IN tags',
        expected: query(
            and(
                or(int('image', 'height', '>', 400), int('image', 'width', '>', 640)),
                tagsContains('image', 'reviewed')
            )
        )
    },

    /* Boolean operators in subexpressions */
    {
        name: 'object detection boolean expression',
        source: 'object_detection(label == "cat" AND width >= 50 AND height >= 40)',
        expected: query(
            objectDetection(
                and(
                    str('object_detection', 'label', '==', 'cat'),
                    int('object_detection', 'width', '>=', 50),
                    int('object_detection', 'height', '>=', 40)
                )
            )
        )
    },
    {
        name: 'object detection alternatives',
        source: 'object_detection(label == "cat" OR label == "dog")',
        expected: query(
            objectDetection(
                or(
                    str('object_detection', 'label', '==', 'cat'),
                    str('object_detection', 'label', '==', 'dog')
                )
            )
        )
    },
    {
        name: 'object detection negation',
        source: 'object_detection(NOT label == "background")',
        expected: query(objectDetection(not(str('object_detection', 'label', '==', 'background'))))
    },

    /* Additional syntax features */
    {
        name: 'single quoted string',
        source: "file_name == 'frame-0001.jpg'",
        expected: query(str('image', 'file_name', '==', 'frame-0001.jpg'))
    },
    {
        name: 'trailing comment',
        source: 'height > 400 # high resolution image',
        expected: query(int('image', 'height', '>', 400))
    },
    {
        name: 'multiline whitespace',
        source: 'height > 400\nAND "reviewed" IN tags\nAND object_detection(label == "cat")',
        expected: query(
            and(
                int('image', 'height', '>', 400),
                tagsContains('image', 'reviewed'),
                objectDetection(str('object_detection', 'label', '==', 'cat'))
            )
        )
    },

    /* Complex queries */
    {
        name: 'complex reviewed large cat image',
        source: 'height > 400 AND width >= 640 AND "reviewed" IN tags AND object_detection(label == "cat" AND width > 80 AND height > 80)',
        expected: query(
            and(
                int('image', 'height', '>', 400),
                int('image', 'width', '>=', 640),
                tagsContains('image', 'reviewed'),
                objectDetection(
                    and(
                        str('object_detection', 'label', '==', 'cat'),
                        int('object_detection', 'width', '>', 80),
                        int('object_detection', 'height', '>', 80)
                    )
                )
            )
        )
    },
    {
        name: 'complex dataset curation query',
        source: '(file_path_abs != "/datasets/archive/bad.jpg" AND created_at >= "2025-01-01T00:00:00Z") AND ("training" IN tags OR "validation" IN tags) AND object_detection((label == "cat" OR label == "dog") AND NOT (x < 5 OR y < 5))',
        expected: query(
            and(
                str('image', 'file_path_abs', '!=', '/datasets/archive/bad.jpg'),
                dt('image', 'created_at', '>=', '2025-01-01T00:00:00Z'),
                or(tagsContains('image', 'training'), tagsContains('image', 'validation')),
                objectDetection(
                    and(
                        or(
                            str('object_detection', 'label', '==', 'cat'),
                            str('object_detection', 'label', '==', 'dog')
                        ),
                        not(
                            or(
                                int('object_detection', 'x', '<', 5),
                                int('object_detection', 'y', '<', 5)
                            )
                        )
                    )
                )
            )
        )
    }
];

describe.skip('parseLightlyQuery translates example queries', () => {
    it.each(TRANSLATION_TEST_CASES)('$name', ({ source, expected }) => {
        const result = parseLightlyQuery(parser, source);
        expect(result).toEqual({ status: 'ok', queryExpr: expected });
    });
});
