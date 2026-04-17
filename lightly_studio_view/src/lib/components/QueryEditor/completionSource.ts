import type { CompletionContext, CompletionResult } from '@codemirror/autocomplete';
import { syntaxTree } from '@codemirror/language';
import type { QuerySchema } from '$lib/hooks/useQuerySchema/useQuerySchema';

const BOOLEAN_OPS = [
    { label: 'and', type: 'keyword' },
    { label: 'or', type: 'keyword' },
    { label: 'not', type: 'keyword' }
];

const SUBQUERY_KEYWORDS = [
    { label: 'has_tag(', type: 'keyword', apply: 'has_tag("' },
    { label: 'has_annotation(', type: 'keyword', apply: 'has_annotation(' }
];

function getFieldCompletions(schema: QuerySchema, inAnnotation: boolean) {
    const fields = inAnnotation ? (schema.subcontexts?.annotation ?? []) : schema.fields;
    return fields.map((f) => ({
        label: f.name,
        type: 'property',
        detail: f.field_type
    }));
}

function getOperatorCompletions(fieldName: string, schema: QuerySchema, inAnnotation: boolean) {
    const fields = inAnnotation ? (schema.subcontexts?.annotation ?? []) : schema.fields;
    const field = fields.find((f) => f.name === fieldName);
    if (!field) return [];
    return field.operators.map((op) => ({ label: op, type: 'operator' }));
}

function isInsideHasAnnotation(tree: ReturnType<typeof syntaxTree>, pos: number): boolean {
    let node = tree.resolveInner(pos, -1);
    while (node) {
        if (node.name === 'HasAnnotation') return true;
        if (!node.parent) break;
        node = node.parent;
    }
    return false;
}

export function buildCompletionSource(getSchema: () => QuerySchema | undefined) {
    return function completionSource(context: CompletionContext): CompletionResult | null {
        const schema = getSchema();
        if (!schema) return null;

        const tree = syntaxTree(context.state);
        const node = tree.resolveInner(context.pos, -1);
        const inAnnotation = isInsideHasAnnotation(tree, context.pos);

        // After a field name, suggest operators
        if (node.name === 'FieldRef' || node.name === 'Identifier') {
            const parent = node.parent;
            if (parent?.name === 'Comparison') {
                // Cursor is at the field ref in a comparison — suggest operators
                const fieldText = context.state.sliceDoc(parent.from, node.to);
                const opCompletions = getOperatorCompletions(fieldText, schema, inAnnotation);
                if (opCompletions.length > 0) {
                    const wordMatch = context.matchBefore(/\S*/);
                    return {
                        from: wordMatch ? wordMatch.from : context.pos,
                        options: opCompletions
                    };
                }
            }
        }

        // Inside CompOp node — suggest operators for the current field
        if (node.name === 'CompOp' || node.name === 'CmpOpToken') {
            const comparison = node.parent;
            if (comparison?.name === 'Comparison') {
                const fieldRef = comparison.firstChild;
                const fieldText = fieldRef
                    ? context.state.sliceDoc(fieldRef.from, fieldRef.to)
                    : '';
                const opCompletions = getOperatorCompletions(fieldText, schema, inAnnotation);
                const wordMatch = context.matchBefore(/[\w><=!]+/);
                return {
                    from: wordMatch ? wordMatch.from : context.pos,
                    options: opCompletions
                };
            }
        }

        // At start of expression or after boolean op — suggest fields and subqueries
        const word = context.matchBefore(/[\w_]*/);
        if (!word && !context.explicit) return null;

        const from = word ? word.from : context.pos;
        const options = [
            ...getFieldCompletions(schema, inAnnotation),
            ...(!inAnnotation ? SUBQUERY_KEYWORDS : []),
            ...BOOLEAN_OPS
        ];

        return { from, options };
    };
}
