import { COLLECTION_OVERVIEW, type Suggestion } from './AgentChatSuggestions/suggestions';

const CLASS_DISTRIBUTION: Suggestion = {
    label: 'See class distribution',
    prompt: 'Show how many samples have each annotation class in the full collection.'
};

const VIEW_ALL: Suggestion = {
    label: 'View all images',
    prompt: 'Show all images in the collection.'
};

const ANNOTATION_HELP: Suggestion = {
    label: 'Learn about annotations',
    prompt: 'How do I add and review annotations in LightlyStudio?'
};

/** Offers actions supported by the current collection or the latest tool result. */
export function suggestFromToolResult(
    toolName: string,
    result: Record<string, unknown>
): Suggestion[] {
    switch (toolName) {
        case 'get_collection_overview':
        case 'list_annotation_classes':
            return suggestFromOverview(result);
        case 'run_selection':
        case 'tag_samples':
            return suggestFromTag(result.tag_name);
        case 'get_distribution':
            return [VIEW_ALL, COLLECTION_OVERVIEW];
        default:
            return [CLASS_DISTRIBUTION, COLLECTION_OVERVIEW];
    }
}

function suggestFromOverview(result: Record<string, unknown>): Suggestion[] {
    const firstClass = Array.isArray(result.annotation_classes)
        ? result.annotation_classes[0]?.name
        : undefined;
    const suggestions = [
        typeof firstClass === 'string' && firstClass.trim()
            ? {
                  label: `View ${firstClass} samples`,
                  prompt: `Show samples with annotations of class ${JSON.stringify(firstClass)}.`
              }
            : ANNOTATION_HELP
    ];

    suggestions.push(typeof firstClass === 'string' ? CLASS_DISTRIBUTION : VIEW_ALL);
    if (Array.isArray(result.embedding_models) && result.embedding_models.length) {
        suggestions.push({
            label: 'Select a diverse subset',
            prompt: 'I want to select a diverse subset of samples.'
        });
    }
    return suggestions;
}

function suggestFromTag(tagName: unknown): Suggestion[] {
    if (typeof tagName !== 'string' || !tagName.trim()) return [CLASS_DISTRIBUTION, VIEW_ALL];
    return [
        {
            label: 'Compare with full collection',
            prompt: `Compare the annotation class distribution of samples tagged ${JSON.stringify(tagName)} with the full collection.`
        },
        VIEW_ALL
    ];
}
