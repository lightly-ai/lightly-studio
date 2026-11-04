import { describe, expect, it } from 'vitest';
import { createLightlyQueryServices } from './lightly-query-module';
import { parseLightlyQuery } from './query-expr-translation';

const parser = createLightlyQueryServices().LightlyQuery.parser.LangiumParser;
const metric = (metric_name: string, operator = '==', value = 0) => ({
    type: 'evaluation_metric_comparison_expr',
    metric_name,
    operator,
    value
});
const evaluation = (criteria: unknown[] = []) => ({
    type: 'sample_evaluation_match_expr',
    run_name: 'run1',
    criteria
});
const parse = (source: string) => parseLightlyQuery(parser, source);
const ok = (match_expr: unknown) => ({ status: 'ok', queryExpr: { match_expr } });

describe('sample evaluation query translation', () => {
    it('preserves video fps filters alongside bare fp metrics', () => {
        expect(parse('video: fps = 30').status).toBe('ok');
        expect(
            parse('video: fps = 30 AND sample_evaluation(name = "run1" AND fp = 0)').status
        ).toBe('ok');
    });

    it('translates quoted metrics into run-scoped criteria', () => {
        expect(
            parse('sample_evaluation(name = "run1" AND "tp" >= 1 AND "fn" >= 5 AND "fp" = 0)')
        ).toEqual(
            ok(
                evaluation([
                    {
                        type: 'and',
                        children: [metric('tp', '>=', 1), metric('fn', '>=', 5), metric('fp')]
                    }
                ])
            )
        );
    });

    it('supports name-only queries in image and video scope', () => {
        expect(parse('sample_evaluation(name = "run1")')).toEqual(ok(evaluation()));
        expect(parse("video: sample_evaluation(name = 'run1')")).toEqual(ok(evaluation()));
    });

    it.each(['=', '!=', '<', '<=', '>', '>='])('translates %s and signed decimals', (operator) => {
        expect(
            parse(`sample_evaluation(name = "run1" AND "custom_score" ${operator} -0.5)`)
        ).toEqual(
            ok(evaluation([metric('custom_score', operator === '=' ? '==' : operator, -0.5)]))
        );
    });

    it.each(['custom-score', 'width', 'name', 'AND', 'metric with spaces'])(
        'accepts quoted metric %s',
        (name) => {
            expect(parse(`sample_evaluation(name = "run1" AND "${name}" > +2)`)).toEqual(
                ok(evaluation([metric(name, '>', 2)]))
            );
        }
    );

    it('accepts mixed-case Boolean operators', () => {
        expect(
            parse('sample_evaluation(name = "run1" aNd "width_score" > 1 or "NOTable" = 0)')
        ).toEqual(
            ok(
                evaluation([
                    { type: 'or', children: [metric('width_score', '>', 1), metric('NOTable')] }
                ])
            )
        );
    });

    it('preserves Boolean precedence and inner versus outer negation', () => {
        expect(
            parse(
                'NOT sample_evaluation(name = "run1" AND "tp" > 1 OR NOT ("fp" = 0 AND "fn" != 2))'
            )
        ).toEqual(
            ok({
                type: 'not',
                child: evaluation([
                    {
                        type: 'or',
                        children: [
                            metric('tp', '>', 1),
                            {
                                type: 'not',
                                child: {
                                    type: 'and',
                                    children: [metric('fp'), metric('fn', '!=', 2)]
                                }
                            }
                        ]
                    }
                ])
            })
        );
    });

    it('combines sample fields and independently scoped runs', () => {
        expect(
            parse(
                'width >= 640 AND (sample_evaluation(name = "run1") OR sample_evaluation(name = "run2"))'
            )
        ).toEqual(
            ok({
                type: 'and',
                children: [
                    {
                        type: 'integer_expr',
                        field: { table: 'image', name: 'width' },
                        operator: '>=',
                        value: 640
                    },
                    { type: 'or', children: [evaluation(), { ...evaluation(), run_name: 'run2' }] }
                ]
            })
        );
    });

    it.each([
        '',
        '"tp" > 0',
        'name != "run1"',
        'name = 1',
        'name = "run1" OR "tp" > 0',
        'name = "run1" AND name = "run2"',
        'name = "run1" AND "tp" = "1"',
        'name = "run1" AND "tp" = true',
        'name = "run1" AND "tp" = NaN',
        'name = "run1" AND "tp" = Infinity',
        'name = "run1" AND width > 0',
        'name = "run1" AND metadata["tp"] > 0',
        'name = "run1" AND "tag" IN tags',
        'name = "run1" AND sample_evaluation(name = "run2")',
        'name = "run1" AND classification(class_name = "cat")'
    ])('rejects invalid evaluation criteria: %s', (body) => {
        expect(parse(`sample_evaluation(${body})`).status).toBe('error');
    });

    it.each(['custom_score', 'width', 'name', 'tp_score', 'fp_extra', 'fn_count'])(
        'rejects unquoted metric %s',
        (name) => {
            expect(parse(`sample_evaluation(name = "run1" AND ${name} > 0)`).status).toBe('error');
        }
    );

    it.each(['tp', 'fp', 'fn'])('accepts bare and quoted built-in metric %s', (name) => {
        const expected = ok(evaluation([metric(name, '>', 1)]));
        expect(parse(`sample_evaluation(name = "run1" AND ${name} > 1)`)).toEqual(expected);
        expect(parse(`sample_evaluation(name = "run1" AND "${name}" > 1)`)).toEqual(expected);
    });

    it('accepts single-quoted metric names', () => {
        expect(parse("sample_evaluation(name = 'run1' AND 'custom_score' > 1)")).toEqual(
            ok(evaluation([metric('custom_score', '>', 1)]))
        );
    });

    it.each(['object_detection', 'classification', 'segmentation_mask'])(
        'rejects evaluation within %s',
        (name) => {
            expect(parse(`${name}(sample_evaluation(name = "run1"))`).status).toBe('error');
        }
    );

    it('rejects overflowing numeric thresholds', () => {
        expect(parse(`sample_evaluation(name = "run1" AND "tp" > ${'9'.repeat(400)})`).status).toBe(
            'error'
        );
    });
});
