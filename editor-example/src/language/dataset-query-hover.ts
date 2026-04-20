import { AstNode, AstNodeHoverProvider } from 'langium';
import { Hover, MarkupContent } from 'vscode-languageserver';
import type { DatasetQueryExpression, QueryFunction, FieldAccess } from './generated/ast.js';

/**
 * Provides hover information when user hovers over code elements.
 */
export class DatasetQueryHoverProvider extends AstNodeHoverProvider {

    protected getAstNodeHoverContent(node: AstNode): Hover | undefined {
        if (node.$type === 'DatasetQueryExpression') {
            return this.createHover(
                'Dataset Query',
                'Build a query for the current dataset and combine annotation filters, metadata constraints, and sorting.\n\n' +
                '**Syntax:** `dataset.query().match(...).order_by(...)`\n\n' +
                '**Example:**\n```python\n' +
                'dataset.query().match(\n' +
                '    ObjectDetectionQuery.match(ObjectDetectionField.label == "cat")\n' +
                ')\n' +
                '```'
            );
        }

        // Hover over query functions (ObjectDetectionQuery.match, etc.)
        if (node.$type === 'QueryFunction') {
            const queryFunc = node as QueryFunction;
            if (queryFunc.type === 'ObjectDetectionQuery') {
                if (queryFunc.method === 'match') {
                    return this.createHover(
                        'ObjectDetectionQuery.match',
                        'Filter images that have at least one annotation matching the condition.\n\n' +
                        '**Returns:** Boolean filter expression\n\n' +
                        '**Example:**\n```python\n' +
                        'ObjectDetectionQuery.match(ObjectDetectionField.label == "cat")\n' +
                        '```'
                    );
                } else if (queryFunc.method === 'count') {
                    return this.createHover(
                        'ObjectDetectionQuery.count',
                        'Count the number of annotations matching the condition.\n\n' +
                        '**Returns:** Integer count (use with comparison operators)\n\n' +
                        '**Example:**\n```python\n' +
                        'ObjectDetectionQuery.count(ObjectDetectionField.label == "cat") >= 2\n' +
                        '```'
                    );
                }
            }
        }

        // Hover over field access (ImageSampleField.width, etc.)
        if (node.$type === 'FieldAccess') {
            const fieldAccess = node as FieldAccess;
            if (fieldAccess.type === 'ImageSampleField') {
                const fieldDocs: Record<string, string> = {
                    'width': 'Image width in pixels',
                    'height': 'Image height in pixels',
                    'created_at': 'Timestamp when the image was created',
                    'file_name': 'Name of the image file',
                    'tags': 'Tags associated with the image'
                };
                const doc = fieldDocs[fieldAccess.field] || 'Image metadata field';
                return this.createHover(
                    `ImageSampleField.${fieldAccess.field}`,
                    doc + '\n\n' +
                    '**Type:** ImageSampleField\n\n' +
                    '**Example:**\n```python\n' +
                    `ImageSampleField.${fieldAccess.field} > 500\n` +
                    '```'
                );
            } else if (fieldAccess.type === 'ObjectDetectionField') {
                const fieldDocs: Record<string, string> = {
                    'label': 'Annotation class label (e.g., "cat", "dog")',
                    'confidence': 'Detection confidence score (0.0 to 1.0)',
                    'bbox': 'Bounding box coordinates'
                };
                const doc = fieldDocs[fieldAccess.field] || 'Object detection annotation field';
                return this.createHover(
                    `ObjectDetectionField.${fieldAccess.field}`,
                    doc + '\n\n' +
                    '**Type:** ObjectDetectionField\n\n' +
                    '**Example:**\n```python\n' +
                    `ObjectDetectionField.${fieldAccess.field} == "cat"\n` +
                    '```'
                );
            }
        }

        return undefined;
    }

    protected override getKeywordHoverContent(node: AstNode): Hover | undefined {
        if (node.$type !== 'Keyword') {
            return undefined;
        }

        return this.getKeywordHover(node as AstNode & { value: string });
    }

    private getKeywordHover(node: AstNode & { value: string }): Hover | undefined {
        const docs: Record<string, { title: string; content: string }> = {
            dataset: {
                title: 'dataset',
                content:
                    'Dataset object used to start a query for the current dataset.\n\n' +
                    '**Example:**\n```python\n' +
                    'dataset.query()\n' +
                    '```'
            },
            query: {
                title: 'query()',
                content:
                    'Create a query builder from the dataset object.\n\n' +
                    '**Next step:** call `.match(...)` to add filter conditions.'
            },
            match: {
                title: 'match(...)',
                content:
                    'Apply the main filter expression. Only samples matching this expression are returned.\n\n' +
                    '**Example:**\n```python\n' +
                    'dataset.query().match(ImageSampleField.width > 500)\n' +
                    '```'
            },
            order_by: {
                title: 'order_by(...)',
                content:
                    'Sort the matched samples by a field, a query-derived value, or a text-similarity score.'
            },
            AND: {
                title: 'AND(...)',
                content:
                    'Logical conjunction. All nested expressions must be true.'
            },
            OR: {
                title: 'OR(...)',
                content:
                    'Logical disjunction. At least one nested expression must be true.'
            },
            NOT: {
                title: 'NOT(...)',
                content:
                    'Logical negation. Inverts the nested expression.'
            },
            ObjectDetectionQuery: {
                title: 'ObjectDetectionQuery',
                content:
                    'Query helper for object-detection annotations.\n\n' +
                    '**Methods:** `match(...)`, `count(...)`'
            },
            ClassificationQuery: {
                title: 'ClassificationQuery',
                content:
                    'Query helper for classification annotations.\n\n' +
                    '**Methods:** `match(...)`, `count(...)`'
            },
            InstanceSegmentationQuery: {
                title: 'InstanceSegmentationQuery',
                content:
                    'Query helper for instance-segmentation annotations.\n\n' +
                    '**Methods:** `match(...)`, `count(...)`'
            },
            ObjectDetectionField: {
                title: 'ObjectDetectionField',
                content:
                    'Field namespace for object-detection properties such as `label` and `confidence`.'
            },
            ClassificationField: {
                title: 'ClassificationField',
                content:
                    'Field namespace for classification properties.'
            },
            ImageSampleField: {
                title: 'ImageSampleField',
                content:
                    'Field namespace for sample metadata and sample-level helper functions such as `width`, `height`, and `text_similarity(...)`.'
            },
            OrderByField: {
                title: 'OrderByField(...)',
                content:
                    'Wrap a sortable field or query expression so it can be passed to `.order_by(...)`.'
            },
            desc: {
                title: 'desc()',
                content:
                    'Sort in descending order, from larger values to smaller values.'
            },
            asc: {
                title: 'asc()',
                content:
                    'Sort in ascending order, from smaller values to larger values.'
            },
            text_similarity: {
                title: 'text_similarity(...)',
                content:
                    'Compute a text-similarity score for each sample using the provided text query. This is typically used for ranking in `order_by(...)`.'
            }
        };

        const doc = docs[node.value];
        if (!doc) {
            return undefined;
        }

        return this.createHover(doc.title, doc.content);
    }

    private createHover(title: string, content: string): Hover {
        const markupContent: MarkupContent = {
            kind: 'markdown',
            value: `**${title}**\n\n${content}`
        };
        return {
            contents: markupContent
        };
    }
}
