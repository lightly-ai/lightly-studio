import { describe, expect, it } from 'vitest';
import { getCollectionOverview } from './collectionOverview';

describe('getCollectionOverview', () => {
    it.each([
        { listedClasses: 69, expectedClassCount: 69 },
        { listedClasses: 100, expectedClassCount: undefined }
    ])(
        'restores a legacy overview with $listedClasses listed classes',
        ({ listedClasses, expectedClassCount }) => {
            const overview = getCollectionOverview('Show me an overview of this dataset.', [
                {
                    role: 'assistant',
                    tool_calls: [
                        {
                            id: 'overview',
                            type: 'function',
                            function: { name: 'get_collection_overview', arguments: '{}' }
                        }
                    ]
                },
                {
                    role: 'tool',
                    tool_call_id: 'overview',
                    content: JSON.stringify({
                        sample_count: 128,
                        annotation_classes: Array.from({ length: listedClasses }, (_, index) => ({
                            name: `class-${index}`,
                            sample_count: 1
                        }))
                    })
                }
            ]);

            expect(overview?.imageCount).toBe(128);
            expect(overview?.classCount).toBe(expectedClassCount);
        }
    );
});
