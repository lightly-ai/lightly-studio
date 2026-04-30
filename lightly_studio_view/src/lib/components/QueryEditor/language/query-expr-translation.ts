// Shared contract for translating a parsed query into the backend QueryExpr.
// Both sides import this module so the request method and result shape stay
// in sync.
import type { EqualityComparisonOperator, QueryExpr } from '$lib/api/lightly_studio_local';
import {
    isBooleanExpression,
    isComparisonExpression,
    isFieldReference,
    isFunctionCall,
    isImageDateTimeFieldName,
    isImageIntFieldName,
    isImageStringFieldName,
    isNotExpression,
    isNumberLiteral,
    isObjectDetectionIntFieldName,
    isObjectDetectionStringFieldName,
    isStringLiteral,
    isTagInExpression,
    isVideoEqualityFloatFieldName,
    isVideoIntFieldName,
    isVideoOrdinalFloatFieldName,
    isVideoStringFieldName,
    type ComparisonExpression,
    type Expression,
    type Query
} from './generated/ast.js';

export interface QueryParseError {
    message: string;
    line?: number;
    column?: number;
}

export type QueryExprTranslationResult =
    | { status: 'ok'; queryExpr: QueryExpr }
    | { status: 'error'; errors: QueryParseError[] };

type QueryScope = 'image' | 'video' | 'object_detection' | 'classification';

interface TranslationParser {
    parse: (value: string) => {
        lexerErrors: Array<{ message: string; line?: number; column?: number }>;
        parserErrors: Array<{ message: string; line?: number; column?: number }>;
        value: Query;
    };
}

export function parseLightlyQuery(
    parser: TranslationParser,
    value: string
): QueryExprTranslationResult {
    const parseResult = parser.parse(value);
    const errors = [...parseResult.lexerErrors, ...parseResult.parserErrors];
    if (errors.length > 0) {
        return {
            status: 'error',
            errors: errors.map((error) => ({
                message: error.message,
                line: error.line,
                column: error.column
            }))
        };
    }

    try {
        return {
            status: 'ok',
            queryExpr: toQueryExpr(parseResult.value)
        };
    } catch (error) {
        return {
            status: 'error',
            errors: [{ message: toErrorMessage(error) }]
        };
    }
}

/**
 * Converts a Langium AST into a backend-compatible QueryExpr.
 */
function toQueryExpr(parseResult: Query): QueryExpr {
    const table = getRootScope(parseResult);
    return {
        match_expr: visit(parseResult.expression, table)
    };
}

/**
 * Recursively visits the AST nodes of an expression and translates them into a
 * backend-compatible `QueryExpr` structure, scoped to the specified data table.
 *
 * @param expr The current AST expression node to translate.
 * @param table The context scope for field resolution.
 * @returns A structured object representation of the query expression.
 * @throws Error if an unsupported expression type is encountered.
 */
function visit(expr: Expression, table: QueryScope): QueryExpr['match_expr'] {
    if (isBooleanExpression(expr)) {
        return {
            type: toBooleanExprType(expr.operator),
            children: expr.children.map((child) => visit(child, table))
        };
    }
    if (isNotExpression(expr)) {
        return {
            type: 'not',
            child: visit(expr.expression, table)
        };
    }
    if (isComparisonExpression(expr)) {
        return visitComparisonExpression(expr, table);
    }
    if (isTagInExpression(expr)) {
        if (isStringLiteral(expr.tag_name)) {
            return {
                type: 'tags_contains_expr',
                field: { table, name: 'tags' },
                tag_name: expr.tag_name.value
            };
        }
        throw new Error(`Unsupported tag type: ${expr.tag_name}`);
    }
    if (isFunctionCall(expr)) {
        const subTable = getFunctionScope(expr.name);
        const type =
            subTable === 'object_detection'
                ? 'object_detection_match_expr'
                : 'classification_match_expr';
        return {
            type,
            subexpr: visit(expr.args[0], subTable)
        };
    }
    throw new Error(`Unsupported expression type: ${expr.$type}`);
}

function visitComparisonExpression(
    expr: ComparisonExpression,
    table: QueryScope
): QueryExpr['match_expr'] {
    const left = expr.left;
    if (!isFieldReference(left)) {
        throw new Error(`Unsupported expression: ${expr.$type}`);
    }

    let fieldName = left.member;
    const right = expr.right;
    if (isStringLiteral(right)) {
        switch (table) {
            case 'image':
                if (isImageStringFieldName(fieldName)) {
                    return {
                        type: 'string_expr',
                        field: { table, name: fieldName },
                        operator: toEqualityComparisonOperator(expr.operator),
                        value: right.value
                    };
                }
                if (isImageDateTimeFieldName(fieldName)) {
                    return {
                        type: 'datetime_expr',
                        field: { table, name: fieldName },
                        operator: expr.operator,
                        value: parseDatetimeLiteral(right.value)
                    };
                }
                break;
            case 'video':
                if (isVideoStringFieldName(fieldName)) {
                    return {
                        type: 'string_expr',
                        field: { table, name: fieldName },
                        operator: toEqualityComparisonOperator(expr.operator),
                        value: right.value
                    };
                }
                break;
            case 'object_detection':
                if (isObjectDetectionStringFieldName(fieldName)) {
                    return {
                        type: 'string_expr',
                        field: { table, name: fieldName },
                        operator: toEqualityComparisonOperator(expr.operator),
                        value: right.value
                    };
                }
                break;
            case 'classification':
                return {
                    type: 'string_expr',
                    field: { table, name: fieldName },
                    operator: toEqualityComparisonOperator(expr.operator),
                    value: right.value
                };
        }
    }

    if (isNumberLiteral(right)) {
        switch (table) {
            case 'image':
                if (isImageIntFieldName(fieldName)) {
                    return {
                        type: 'integer_expr',
                        field: { table, name: fieldName },
                        operator: expr.operator,
                        value: right.value
                    };
                }
                break;
            case 'video':
                if (isVideoOrdinalFloatFieldName(fieldName)) {
                    return {
                        type: 'ordinal_float_expr',
                        field: { table, name: fieldName },
                        operator: expr.operator,
                        value: right.value
                    };
                }
                if (isVideoEqualityFloatFieldName(fieldName)) {
                    return {
                        type: 'equality_float_expr',
                        field: { table, name: fieldName },
                        // TODO: make Langium grammar more strict, so that `toEqualityComparisonOperator` is not needed
                        operator: toEqualityComparisonOperator(expr.operator),
                        value: right.value
                    };
                }
                if (isVideoIntFieldName(fieldName)) {
                    return {
                        type: 'integer_expr',
                        field: { table, name: fieldName },
                        operator: expr.operator,
                        value: right.value
                    };
                }
                break;
            case 'object_detection':
                if (isObjectDetectionIntFieldName(fieldName)) {
                    return {
                        type: 'integer_expr',
                        field: { table, name: fieldName },
                        operator: expr.operator,
                        value: right.value
                    };
                }
                break;
            case 'classification':
                break;
        }
    }

    throw new Error(`Unsupported comparison: ${fieldName} ${expr.operator} ${right.$type}`);
}

function getRootScope(parseResult: Query): Extract<QueryScope, 'image' | 'video'> {
    return parseResult.isVideo ? 'video' : 'image';
}

function getFunctionScope(
    name: string
): Extract<QueryScope, 'object_detection' | 'classification'> {
    if (name === 'object_detection' || name === 'classification') {
        return name;
    }

    throw new Error(`Unsupported function: ${name}`);
}

function toBooleanExprType(operator: string): 'and' | 'or' {
    const normalizedOperator = operator.toLowerCase();
    if (normalizedOperator === 'and' || normalizedOperator === 'or') {
        return normalizedOperator;
    }

    throw new Error(`Unsupported boolean operator: ${operator}`);
}

function toEqualityComparisonOperator(operator: string): EqualityComparisonOperator {
    if (operator === '==' || operator === '!=') {
        return operator;
    }

    throw new Error(`Unsupported equality operator: ${operator}`);
}

function parseDatetimeLiteral(value: string): Date {
    // TODO(lukas, 04/2026): Replace this with a stricter ISO 8601 parser to avoid
    // environment-dependent parsing. We might be able to also validate the format in Langium.
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
        throw new Error(`Invalid datetime literal: ${value}`);
    }

    return parsed;
}

function toErrorMessage(error: unknown): string {
    if (error instanceof Error) {
        return error.message;
    }

    return 'Unknown query translation error';
}
