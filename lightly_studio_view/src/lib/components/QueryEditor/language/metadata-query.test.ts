import { describe, expect, it } from 'vitest';
import { createLightlyQueryServices } from './lightly-query-module';
import { parseLightlyQuery } from './query-expr-translation';

const parser = createLightlyQueryServices().LightlyQuery.parser.LangiumParser;

function metadata(path: string, operator: string, value: string | number | boolean) {
    return { type: 'metadata_comparison_expr', path, operator, value };
}

describe('metadata query translation', () => {
    it.each([
        ['metadata["camera"] = "front"', metadata('camera', '==', 'front')],
        ["metadata['camera'] != 'rear'", metadata('camera', '!=', 'rear')],
        ['metadata["reviewed"] = true', metadata('reviewed', '==', true)],
        ['metadata["reviewed"] != false', metadata('reviewed', '!=', false)],
        ['metadata["count"] = 3', metadata('count', '==', 3)],
        ['metadata["count"] != -2', metadata('count', '!=', -2)],
        ['metadata["score"] >= 0.8', metadata('score', '>=', 0.8)],
        ['metadata["score"] > +0.8', metadata('score', '>', 0.8)],
        ['metadata["odometry.acc[1]"] < -0.2', metadata('odometry.acc[1]', '<', -0.2)],
        ['metadata["score"] <= -0.0', metadata('score', '<=', -0)],
        ['metadata["camera name"] = "front left"', metadata('camera name', '==', 'front left')],
        [String.raw`metadata["camera\"name"] = "front"`, metadata('camera"name', '==', 'front')],
        [String.raw`metadata['camera\\name'] = 'front'`, metadata('camera\\name', '==', 'front')],
        ['metadata["reviewed"] = "true"', metadata('reviewed', '==', 'true')]
    ])('translates %s to the exact API payload', (source, expected) => {
        expect(parseLightlyQuery(parser, source)).toEqual({
            status: 'ok',
            queryExpr: { match_expr: expected }
        });
    });

    it.each(['', 'video: '])('preserves NOT, AND, and OR precedence in %s queries', (prefix) => {
        expect(
            parseLightlyQuery(
                parser,
                `${prefix}NOT metadata["camera"] = "front" OR width >= 640 AND metadata["score"] >= 0.8`
            )
        ).toEqual({
            status: 'ok',
            queryExpr: {
                match_expr: {
                    type: 'or',
                    children: [
                        { type: 'not', child: metadata('camera', '==', 'front') },
                        {
                            type: 'and',
                            children: [
                                {
                                    type: 'integer_expr',
                                    field: { table: prefix ? 'video' : 'image', name: 'width' },
                                    operator: '>=',
                                    value: 640
                                },
                                metadata('score', '>=', 0.8)
                            ]
                        }
                    ]
                }
            }
        });
    });

    it('preserves parentheses and composes with annotations and tags', () => {
        expect(
            parseLightlyQuery(
                parser,
                '(metadata["reviewed"] = true OR metadata["score"] < -1) AND "training" IN tags AND classification(class_name = "cat")'
            )
        ).toEqual({
            status: 'ok',
            queryExpr: {
                match_expr: {
                    type: 'and',
                    children: [
                        {
                            type: 'or',
                            children: [metadata('reviewed', '==', true), metadata('score', '<', -1)]
                        },
                        {
                            type: 'tags_contains_expr',
                            field: { table: 'image', name: 'tags' },
                            tag_name: 'training'
                        },
                        {
                            type: 'classification_match_expr',
                            subexpr: {
                                type: 'string_expr',
                                field: { table: 'classification', name: 'class_name' },
                                operator: '==',
                                value: 'cat'
                            }
                        }
                    ]
                }
            }
        });
    });

    it.each([
        'metadata["camera"] < "front"',
        'metadata["reviewed"] >= true',
        'metadata["camera"] == "front"',
        'metadata[camera] = "front"',
        'metadata["camera" = "front"',
        'metadata["camera"]',
        'metadata["camera"] =',
        'metadata["camera"] = null',
        'metadata["camera"] IN ("front")',
        'metadata.camera = "front"',
        'metadata["score"] = --1',
        'metadata["score"] = NaN',
        'metadata["score"] = Infinity',
        'metadata["score"] = "unterminated',
        'object_detection(metadata["score"] > 0.5)',
        'classification(metadata["reviewed"] = true)',
        'segmentation_mask(metadata["camera"] = "front")'
    ])('rejects unsupported syntax: %s', (source) => {
        expect(parseLightlyQuery(parser, source).status).toBe('error');
    });

    it('rejects numeric overflow before serializing a nonfinite value', () => {
        expect(parseLightlyQuery(parser, `metadata["score"] = ${'9'.repeat(400)}.0`)).toEqual({
            status: 'error',
            errors: [{ message: 'Metadata comparison requires a finite number' }]
        });
    });
});
