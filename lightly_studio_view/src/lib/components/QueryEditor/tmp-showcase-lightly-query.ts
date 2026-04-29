import assert from 'node:assert';
import { inject, EmptyFileSystem } from 'langium';
import {
    createDefaultModule,
    createDefaultSharedModule,
    type LangiumServices,
    type LangiumSharedServices
} from 'langium/lsp';
import {
    LightlyQueryGeneratedSharedModule,
    LightlyQueryGeneratedModule
} from './language/generated/module';
import {
    type Query,
    isFieldReference,
    isBooleanExpression,
    isComparisonExpression,
    isFunctionCall,
    isMemberCall,
    isQualifiedFieldReference,
    isTagInExpression,
    isNumberLiteral,
    isStringLiteral,
    isNotExpression
} from './language/generated/ast';

export type LightlyQueryServices = LangiumServices;

export function createLightlyQueryServices(): {
    shared: LangiumSharedServices;
    LightlyQuery: LightlyQueryServices;
} {
    const shared = inject(
        createDefaultSharedModule(EmptyFileSystem),
        LightlyQueryGeneratedSharedModule
    );
    const LightlyQuery = inject(createDefaultModule({ shared }), LightlyQueryGeneratedModule);
    shared.ServiceRegistry.register(LightlyQuery);
    return { shared, LightlyQuery };
}

function unquoteStringLiteral(value: string): string {
    if (
        (value.startsWith('"') && value.endsWith('"')) ||
        (value.startsWith("'") && value.endsWith("'"))
    ) {
        return value.slice(1, -1);
    }
    return value;
}

type DSLJson =
    | boolean
    | number
    | string
    | null
    | {
          kind: string;
          annotation_type?: string;
          criterion?: DSLJson;
          field?: string;
          operator?: string;
          tag_name?: DSLJson;
          term?: DSLJson;
          terms?: DSLJson[];
          value?: DSLJson;
      };

function hasName(node: unknown): node is { name: string } {
    return (
        typeof node === 'object' && node !== null && 'name' in node && typeof node.name === 'string'
    );
}

function hasExpression(node: unknown): node is { expression: unknown } {
    return typeof node === 'object' && node !== null && 'expression' in node;
}

function transformToDSLJson(node: unknown): DSLJson {
    if (isBooleanExpression(node)) {
        return {
            kind: node.operator.toUpperCase(),
            terms: node.children.map((child) => transformToDSLJson(child))
        };
    }
    if (isNotExpression(node)) {
        return {
            kind: 'NOT',
            term: transformToDSLJson(node.expression)
        };
    }
    if (isComparisonExpression(node)) {
        const left = node.left;
        let field = '';
        if (isQualifiedFieldReference(left)) {
            field = left.member;
        } else if (isMemberCall(left)) {
            if (left.receiver === 'ObjectDetection' || left.receiver === 'ObjectDetectionField') {
                field = left.member;
            } else {
                field = left.receiver || (hasName(left) ? left.name : 'unknown_field');
            }
        } else if (isFieldReference(left)) {
            field = left.name;
        } else {
            field = hasName(left) ? left.name : 'unknown_field';
        }
        return {
            kind: 'COMPARISON',
            field: field,
            operator: node.operator,
            value: transformToDSLJson(node.right)
        };
    }
    if (isFunctionCall(node)) {
        return {
            kind: 'ANNOTATION_QUERY',
            annotation_type: node.name,
            criterion: node.args.length > 0 ? transformToDSLJson(node.args[0]) : null
        };
    }
    if (isTagInExpression(node)) {
        return {
            kind: 'TAGS_CONTAINS',
            tag_name: transformToDSLJson(node.tag_name)
        };
    }
    if (isNumberLiteral(node)) return node.value;
    if (isStringLiteral(node)) return unquoteStringLiteral(node.value);

    if (hasExpression(node)) return transformToDSLJson(node.expression);

    console.warn('transformToDSLJson: Unhandled node type', node);
    return null;
}

const services = createLightlyQueryServices().LightlyQuery;

const parser = services.parser.LangiumParser;

const queries = [
    "(Image.width > 100 OR Image.height > 100 OR Image.created_at == '2026-04-23 12:47:18+02:00') AND object_detection(label == 'car')",
    "'dog' in tags OR 'cat' IN tags AND Image.width > 100",
    "'dog' in tags OR ('cat' IN tags AND Image.width >= 12)",
    "video: NOT (Video.fps != 30.0 AND NOT 'low_res' IN tags)",
    "object_detection(label == 'car' AND x < 10 OR label == 'truck' AND width > 100)",
    'object_detection(ObjectDetection.width > 50 AND ObjectDetection.height < 200)'
];

const expectedOutputs = [
    {
        kind: 'AND',
        terms: [
            {
                kind: 'OR',
                terms: [
                    {
                        kind: 'COMPARISON',
                        field: 'width',
                        operator: '>',
                        value: 100
                    },
                    {
                        kind: 'COMPARISON',
                        field: 'height',
                        operator: '>',
                        value: 100
                    },
                    {
                        kind: 'COMPARISON',
                        field: 'created_at',
                        operator: '==',
                        value: '2026-04-23 12:47:18+02:00'
                    }
                ]
            },
            {
                kind: 'ANNOTATION_QUERY',
                annotation_type: 'object_detection',
                criterion: {
                    kind: 'COMPARISON',
                    field: 'label',
                    operator: '==',
                    value: 'car'
                }
            }
        ]
    },
    {
        kind: 'OR',
        terms: [
            {
                kind: 'TAGS_CONTAINS',
                tag_name: 'dog'
            },
            {
                kind: 'AND',
                terms: [
                    {
                        kind: 'TAGS_CONTAINS',
                        tag_name: 'cat'
                    },
                    {
                        kind: 'COMPARISON',
                        field: 'width',
                        operator: '>',
                        value: 100
                    }
                ]
            }
        ]
    },
    {
        kind: 'OR',
        terms: [
            {
                kind: 'TAGS_CONTAINS',
                tag_name: 'dog'
            },
            {
                kind: 'AND',
                terms: [
                    {
                        kind: 'TAGS_CONTAINS',
                        tag_name: 'cat'
                    },
                    {
                        kind: 'COMPARISON',
                        field: 'width',
                        operator: '>=',
                        value: 12
                    }
                ]
            }
        ]
    },
    {
        kind: 'NOT',
        term: {
            kind: 'AND',
            terms: [
                {
                    kind: 'COMPARISON',
                    field: 'fps',
                    operator: '!=',
                    value: 30.0
                },
                {
                    kind: 'NOT',
                    term: {
                        kind: 'TAGS_CONTAINS',
                        tag_name: 'low_res'
                    }
                }
            ]
        }
    },
    {
        kind: 'ANNOTATION_QUERY',
        annotation_type: 'object_detection',
        criterion: {
            kind: 'OR',
            terms: [
                {
                    kind: 'AND',
                    terms: [
                        {
                            kind: 'COMPARISON',
                            field: 'label',
                            operator: '==',
                            value: 'car'
                        },
                        {
                            kind: 'COMPARISON',
                            field: 'x',
                            operator: '<',
                            value: 10
                        }
                    ]
                },
                {
                    kind: 'AND',
                    terms: [
                        {
                            kind: 'COMPARISON',
                            field: 'label',
                            operator: '==',
                            value: 'truck'
                        },
                        {
                            kind: 'COMPARISON',
                            field: 'width',
                            operator: '>',
                            value: 100
                        }
                    ]
                }
            ]
        }
    },
    {
        kind: 'ANNOTATION_QUERY',
        annotation_type: 'object_detection',
        criterion: {
            kind: 'AND',
            terms: [
                {
                    kind: 'COMPARISON',
                    field: 'width',
                    operator: '>',
                    value: 50
                },
                {
                    kind: 'COMPARISON',
                    field: 'height',
                    operator: '<',
                    value: 200
                }
            ]
        }
    }
];

console.log('=== Langium-Powered LightlyQuery DSL Showcase ===');
console.log('');

queries.forEach((q, i) => {
    console.log('Query ' + (i + 1) + ': ' + q);
    const parseResult = parser.parse<Query>(q);

    if (parseResult.lexerErrors.length > 0 || parseResult.parserErrors.length > 0) {
        console.error('Errors encountered during parsing:');
        parseResult.lexerErrors.forEach((err) => console.error('Lexer Error: ' + err.message));
        parseResult.parserErrors.forEach((err) => console.error('Parser Error: ' + err.message));
    } else {
        const json = transformToDSLJson(parseResult.value);
        console.log('Emitted JSON for Backend:');
        console.log(JSON.stringify(json, null, 2));

        // Verify output matches expected output
        assert.deepStrictEqual(
            json,
            expectedOutputs[i],
            'Output JSON for Query ' + (i + 1) + ' does not match expected output.'
        );
    }
    console.log('\n-----------------------------------\n');
});
