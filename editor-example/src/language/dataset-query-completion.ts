import { CompletionAcceptor, CompletionContext, CompletionValueItem, DefaultCompletionProvider, NextFeature } from 'langium';
import { CompletionItem, CompletionItemKind } from 'vscode-languageserver';

/**
 * Provides autocomplete suggestions based on context.
 */
export class DatasetQueryCompletionProvider extends DefaultCompletionProvider {

    protected override completionFor(
        context: CompletionContext,
        next: NextFeature,
        acceptor: CompletionAcceptor
    ): void {
        // Get the text before the cursor
        const text = context.textDocument.getText();
        const offset = context.offset;
        const textBeforeCursor = text.substring(0, offset);

        // Autocomplete after "dataset."
        if (textBeforeCursor.endsWith('dataset.')) {
            this.completeDatasetMethods(acceptor);
            return;
        }

        // Autocomplete after "ObjectDetectionQuery."
        if (textBeforeCursor.endsWith('ObjectDetectionQuery.')) {
            this.completeQueryMethods(acceptor);
            return;
        }

        // Autocomplete after "ObjectDetectionField."
        if (textBeforeCursor.endsWith('ObjectDetectionField.')) {
            this.completeObjectDetectionFields(acceptor);
            return;
        }

        // Autocomplete after "ImageSampleField."
        if (textBeforeCursor.endsWith('ImageSampleField.')) {
            this.completeImageSampleFields(acceptor);
            return;
        }

        // Autocomplete after "ClassificationField."
        if (textBeforeCursor.endsWith('ClassificationField.')) {
            this.completeClassificationFields(acceptor);
            return;
        }

        // Autocomplete after "OrderByField."
        if (textBeforeCursor.endsWith('OrderByField.')) {
            this.completeSortDirections(acceptor);
            return;
        }

        // Check if we're after a closing parenthesis for order_by suggestion
        if (textBeforeCursor.match(/\)\.$/)) {
            this.completeQueryChainMethods(acceptor);
            return;
        }

        // Fall back to default completion
        super.completionFor(context, next, acceptor);
    }

    private completeDatasetMethods(acceptor: CompletionAcceptor): void {
        acceptor({
            label: 'query',
            kind: CompletionItemKind.Method,
            detail: 'Create a new dataset query',
            documentation: 'Start building a dataset query to filter images',
            insertText: 'query().match($0)',
            insertTextFormat: 2 // Snippet format
        });
    }

    private completeQueryMethods(acceptor: CompletionAcceptor): void {
        acceptor({
            label: 'match',
            kind: CompletionItemKind.Method,
            detail: 'ObjectDetectionQuery.match(condition)',
            documentation: 'Filter images with at least one matching annotation',
            insertText: 'match(ObjectDetectionField.label == \"${1:cat}\")',
            insertTextFormat: 2
        });

        acceptor({
            label: 'count',
            kind: CompletionItemKind.Method,
            detail: 'ObjectDetectionQuery.count(condition)',
            documentation: 'Count annotations matching a condition',
            insertText: 'count(ObjectDetectionField.label == \"${1:cat}\") ${2:>=} ${3:1}',
            insertTextFormat: 2
        });
    }

    private completeObjectDetectionFields(acceptor: CompletionAcceptor): void {
        const fields = [
            { label: 'label', detail: 'Annotation class label', example: '"cat"' },
            { label: 'confidence', detail: 'Detection confidence score', example: '0.9' },
            { label: 'bbox_x', detail: 'Bounding box X coordinate', example: '100' },
            { label: 'bbox_y', detail: 'Bounding box Y coordinate', example: '100' },
            { label: 'bbox_width', detail: 'Bounding box width', example: '200' },
            { label: 'bbox_height', detail: 'Bounding box height', example: '200' }
        ];

        for (const field of fields) {
            acceptor({
                label: field.label,
                kind: CompletionItemKind.Property,
                detail: field.detail,
                documentation: `ObjectDetectionField.${field.label} == ${field.example}`,
                insertText: `${field.label} == \${1:${field.example}}`,
                insertTextFormat: 2
            });
        }
    }

    private completeImageSampleFields(acceptor: CompletionAcceptor): void {
        const fields = [
            { label: 'width', detail: 'Image width in pixels', example: '1920' },
            { label: 'height', detail: 'Image height in pixels', example: '1080' },
            { label: 'created_at', detail: 'Image creation timestamp', example: '"2024-01-01"' },
            { label: 'file_name', detail: 'Image file name', example: '"cat.jpg"' },
            { label: 'file_size', detail: 'Image file size in bytes', example: '102400' },
            { label: 'text_similarity', detail: 'Text similarity search', example: '"cat"', isMethod: true }
        ];

        for (const field of fields) {
            if (field.isMethod) {
                acceptor({
                    label: field.label,
                    kind: CompletionItemKind.Method,
                    detail: field.detail,
                    documentation: `ImageSampleField.${field.label}(query)`,
                    insertText: `${field.label}(\${1:${field.example}})`,
                    insertTextFormat: 2
                });
            } else {
                acceptor({
                    label: field.label,
                    kind: CompletionItemKind.Property,
                    detail: field.detail,
                    documentation: `ImageSampleField.${field.label} > ${field.example}`,
                    insertText: `${field.label} \${1:>} \${2:${field.example}}`,
                    insertTextFormat: 2
                });
            }
        }
    }

    private completeClassificationFields(acceptor: CompletionAcceptor): void {
        acceptor({
            label: 'label',
            kind: CompletionItemKind.Property,
            detail: 'Classification label',
            documentation: 'ClassificationField.label == "indoor"',
            insertText: 'label == "${1:indoor}"',
            insertTextFormat: 2
        });

        acceptor({
            label: 'confidence',
            kind: CompletionItemKind.Property,
            detail: 'Classification confidence',
            documentation: 'ClassificationField.confidence > 0.8',
            insertText: 'confidence ${1:>} ${2:0.8}',
            insertTextFormat: 2
        });
    }

    private completeSortDirections(acceptor: CompletionAcceptor): void {
        acceptor({
            label: 'desc',
            kind: CompletionItemKind.Method,
            detail: 'Sort in descending order',
            documentation: 'OrderByField(...).desc()',
            insertText: 'desc()',
            insertTextFormat: 2
        });

        acceptor({
            label: 'asc',
            kind: CompletionItemKind.Method,
            detail: 'Sort in ascending order',
            documentation: 'OrderByField(...).asc()',
            insertText: 'asc()',
            insertTextFormat: 2
        });
    }

    private completeQueryChainMethods(acceptor: CompletionAcceptor): void {
        acceptor({
            label: 'order_by',
            kind: CompletionItemKind.Method,
            detail: 'Sort query results',
            documentation: '.order_by(OrderByField(...))',
            insertText: 'order_by(OrderByField(${1:ImageSampleField.width}).${2:desc}())',
            insertTextFormat: 2
        });
    }
}
