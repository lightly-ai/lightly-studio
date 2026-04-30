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
    isQualifiedFieldReference,
    isBooleanExpression,
    isComparisonExpression,
    isFunctionCall,
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
          type?: 'image' | 'video' | 'object_detection';
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

function transformToDSLJson(
    node: unknown,
    context: 'image' | 'video' | 'object_detection'
): DSLJson {
    if (isBooleanExpression(node)) {
        return {
            kind: node.operator.toUpperCase(),
            terms: node.children.map((child) => transformToDSLJson(child, context))
        };
    }
    if (isNotExpression(node)) {
        return {
            kind: 'NOT',
            term: transformToDSLJson(node.expression, context)
        };
    }
    if (isComparisonExpression(node)) {
        const left = node.left;
        let field = '';
        if (isQualifiedFieldReference(left)) {
            field = left.member;
        } else if (isFieldReference(left)) {
            field = left.name;
            // The grammar already enforces valid fields for the context.
            // We are just forwarding the context to recursive calls.
        } else {
            field = hasName(left) ? left.name : 'unknown_field';
        }
        return {
            kind: 'COMPARISON',
            type: context,
            field: field,
            operator: node.operator,
            value: transformToDSLJson(node.right, context)
        };
    }
    if (isFunctionCall(node)) {
        // There are only annotation function calls, so this is an annotation query.
        assert.strictEqual(node.name, 'object_detection');
        return {
            kind: 'ANNOTATION_QUERY',
            annotation_type: node.name,
            criterion: node.args.length > 0 ? transformToDSLJson(node.args[0], node.name) : null
        };
    }
    if (isTagInExpression(node)) {
        return {
            kind: 'TAGS_CONTAINS',
            type: context,
            tag_name: transformToDSLJson(node.tag_name, context)
        };
    }
    if (isNumberLiteral(node)) return node.value;
    if (isStringLiteral(node)) return unquoteStringLiteral(node.value);

    if (hasExpression(node)) return transformToDSLJson(node.expression, context);

    console.warn('transformToDSLJson: Unhandled node type', node);
    return null;
}

const services = createLightlyQueryServices().LightlyQuery;

const parser = services.parser.LangiumParser;

const queries = [
    "(width > 100 OR height > 100 OR created_at == '2026-04-23 12:47:18+02:00') AND object_detection(label == 'car')",
    "'dog' in tags OR 'cat' IN tags AND width > 100",
    "'dog' in tags OR ('cat' IN tags AND width >= 12)",
    "video: NOT (fps != 30.0 AND NOT 'low_res' IN tags)",
    "object_detection(label == 'car' AND x < 10 OR label == 'truck' AND width > 100)",
    'object_detection(width > 50 AND height < 200)'
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
                        type: 'image',
                        field: 'width',
                        operator: '>',
                        value: 100
                    },
                    {
                        kind: 'COMPARISON',
                        type: 'image',
                        field: 'height',
                        operator: '>',
                        value: 100
                    },
                    {
                        kind: 'COMPARISON',
                        type: 'image',
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
                    type: 'object_detection',
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
                type: 'image',
                tag_name: 'dog'
            },
            {
                kind: 'AND',
                terms: [
                    {
                        kind: 'TAGS_CONTAINS',
                        type: 'image',
                        tag_name: 'cat'
                    },
                    {
                        kind: 'COMPARISON',
                        type: 'image',
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
                type: 'image',
                tag_name: 'dog'
            },
            {
                kind: 'AND',
                terms: [
                    {
                        kind: 'TAGS_CONTAINS',
                        type: 'image',
                        tag_name: 'cat'
                    },
                    {
                        kind: 'COMPARISON',
                        type: 'image',
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
                    type: 'video',
                    field: 'fps',
                    operator: '!=',
                    value: 30.0
                },
                {
                    kind: 'NOT',
                    term: {
                        kind: 'TAGS_CONTAINS',
                        type: 'video',
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
                            type: 'object_detection',
                            field: 'label',
                            operator: '==',
                            value: 'car'
                        },
                        {
                            kind: 'COMPARISON',
                            type: 'object_detection',
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
                            type: 'object_detection',
                            field: 'label',
                            operator: '==',
                            value: 'truck'
                        },
                        {
                            kind: 'COMPARISON',
                            type: 'object_detection',
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
                    type: 'object_detection',
                    field: 'width',
                    operator: '>',
                    value: 50
                },
                {
                    kind: 'COMPARISON',
                    type: 'object_detection',
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
        // Determine initial context
        let initialContext: 'image' | 'video' = 'image';
        if (q.startsWith('video:')) {
            initialContext = 'video';
        }

        const json = transformToDSLJson(parseResult.value, initialContext);
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
