import { AstNode, AstNodeHoverProvider } from 'langium';
import { Hover, MarkupContent } from 'vscode-languageserver';
import type { DatasetQueryExpression, QueryFunction, FieldAccess } from './generated/ast.js';

/**
 * Provides hover information when user hovers over code elements.
 */
export class DatasetQueryHoverProvider extends AstNodeHoverProvider {
    
    protected getAstNodeHoverContent(node: AstNode): Hover | undefined {
        // Hover over dataset.query()
        if (node.$type === 'DatasetQueryExpression') {
            const query = node as DatasetQueryExpression;
            return this.createHover(
                'Dataset Query',
                'Query a dataset to filter images based on annotations, metadata, and other criteria.\n\n' +
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
