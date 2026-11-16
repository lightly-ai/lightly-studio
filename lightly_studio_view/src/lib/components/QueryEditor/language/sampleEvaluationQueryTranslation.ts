import type { EvaluationMetricNotExpr, QueryExpr } from '$lib/api/lightly_studio_local';
import {
    isBooleanExpression,
    isEvaluationMetricComparison,
    isNotExpression,
    type EvaluationMetricComparison,
    type Expression,
    type SampleEvaluationQuery
} from './generated/ast';

type SampleEvaluationExpression = Extract<
    QueryExpr['match_expr'],
    { type: 'sample_evaluation_match_expr' }
>;
// The `child` union keeps the `type` discriminator, unlike the `criteria` items.
type MetricExpression = EvaluationMetricNotExpr['child'];

export function translateSampleEvaluation(expr: SampleEvaluationQuery): SampleEvaluationExpression {
    return {
        type: 'sample_evaluation_match_expr',
        run_name: expr.runName,
        criteria: expr.criteria ? [translateMetric(expr.criteria)] : []
    };
}

function translateMetric(expr: Expression): MetricExpression {
    if (isBooleanExpression(expr)) {
        return {
            type: expr.operator.toLowerCase() === 'and' ? 'and' : 'or',
            children: expr.children.map(translateMetric)
        };
    }
    if (isNotExpression(expr)) {
        return { type: 'not', child: translateMetric(expr.expression) };
    }
    if (isEvaluationMetricComparison(expr)) {
        return translateComparison(expr);
    }
    throw new Error(`Unsupported evaluation metric expression: ${expr.$type}`);
}

function translateComparison(expr: EvaluationMetricComparison): MetricExpression {
    if (!Number.isFinite(expr.value)) {
        throw new Error('Evaluation metric comparison requires a finite number');
    }
    return {
        type: 'evaluation_metric_comparison_expr',
        metric_name: expr.metricName,
        operator: expr.operator === '=' ? '==' : expr.operator,
        value: expr.value
    };
}
