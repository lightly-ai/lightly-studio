import type { AgentMessage } from '$lib/api/lightly_studio_local';
import { COLLECTION_OVERVIEW } from '../../../AgentChatSuggestions/suggestions';
import { completedToolCalls } from '../../../completedToolCalls';
import { SUGGEST_NEXT_STEPS } from '../../../nextStepSuggestions';

interface AnnotationClass {
    name: string;
    imageCount: number;
}

export interface CollectionOverview {
    imageCount: number;
    classCount?: number;
    mostCommon: AnnotationClass[];
    rareClass?: AnnotationClass;
    tags: string[];
    metadata: string[];
    embeddingModels: string[];
}

const REQUEST_PREFIX = /^(?:please )?(?:(?:give|show) me )?(?:(?:a|an|the) )?(?:brief )?/i;
const OVERVIEW_REQUEST =
    /^(?:(?:collection|dataset) (?:overview|summary|stats|statistics)|(?:overview|summary|stats|statistics) (?:of|for) (?:this|the|my) (?:collection|dataset)|summari[sz]e (?:this|the|my) (?:collection|dataset))[.!?]?$/i;
const OVERVIEW_TOOLS = new Set([
    'get_collection_overview',
    'list_annotation_classes',
    SUGGEST_NEXT_STEPS
]);
const TOP_CLASS_COUNT = 3;
// Older saved overviews list up to 100 classes and omit the total.
const LEGACY_CLASS_LIMIT = 100;

export function getCollectionOverview(
    prompt: string,
    messages: AgentMessage[]
): CollectionOverview | undefined {
    const request = prompt.trim().replace(/\s+/g, ' ');
    const subject = request.replace(REQUEST_PREFIX, '');
    if (request !== COLLECTION_OVERVIEW.prompt && !OVERVIEW_REQUEST.test(subject)) return undefined;

    const calls = completedToolCalls(messages);
    if (calls.some(({ call }) => !OVERVIEW_TOOLS.has(call.function.name))) return undefined;
    const overview = calls.find(({ call }) => call.function.name === 'get_collection_overview');
    if (!overview || !isCount(overview.result.sample_count)) return undefined;

    const { result } = overview;
    const classes = readAnnotationClasses(result.annotation_classes);
    return {
        imageCount: overview.result.sample_count,
        classCount: readClassCount(result, classes.length),
        mostCommon: classes.slice(0, TOP_CLASS_COUNT),
        rareClass: classes.slice(TOP_CLASS_COUNT).find(({ imageCount }) => imageCount === 1),
        tags: Array.isArray(result.tags) ? result.tags.filter(isName) : [],
        metadata: readNames(result.metadata, 'key'),
        embeddingModels: readNames(result.embedding_models, 'name')
    };
}

function readClassCount(result: Record<string, unknown>, validClasses: number): number | undefined {
    if (isCount(result.annotation_class_count)) return result.annotation_class_count;
    const listed = result.annotation_classes;
    if (
        Array.isArray(listed) &&
        listed.length === validClasses &&
        validClasses < LEGACY_CLASS_LIMIT
    ) {
        return validClasses;
    }
    return undefined;
}

function readAnnotationClasses(value: unknown): AnnotationClass[] {
    if (!Array.isArray(value)) return [];
    return value.flatMap((item: { name?: unknown; sample_count?: unknown } | null) =>
        isName(item?.name) && isCount(item.sample_count)
            ? [{ name: item.name, imageCount: item.sample_count }]
            : []
    );
}

function readNames(value: unknown, property: 'name' | 'key'): string[] {
    return Array.isArray(value)
        ? value
              .map((item: Partial<Record<typeof property, unknown>> | null) => item?.[property])
              .filter(isName)
        : [];
}

function isName(value: unknown): value is string {
    return typeof value === 'string' && Boolean(value.trim());
}

function isCount(value: unknown): value is number {
    return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0;
}
