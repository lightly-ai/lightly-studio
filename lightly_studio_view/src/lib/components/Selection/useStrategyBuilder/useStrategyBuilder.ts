import type { TagView } from '$lib/services/types';
import { writable } from 'svelte/store';

export type StrategyType =
    | 'diversity'
    | 'typicality'
    | 'similarity'
    | 'metadata_weighting'
    | 'class_balancing';

export interface DiversityParams {
    embedding_model_name: string;
    strength: number;
}

export interface TypicalityParams {
    strength: number;
}

export interface SimilarityParams {
    query_tag_id: string;
    embedding_model_name: string;
    strength: number;
}

export interface MetadataWeightingParams {
    metadata_key: string;
    strength: number;
}

export interface ClassBalancingTargetRow {
    class_name: string;
    weight: number;
}

export interface ClassBalancingParams {
    target_distribution: ClassBalancingTargetRow[];
    strength: number;
}

interface StrategyParamsByType {
    diversity: DiversityParams;
    typicality: TypicalityParams;
    similarity: SimilarityParams;
    metadata_weighting: MetadataWeightingParams;
    class_balancing: ClassBalancingParams;
}

export type StrategyInstance = {
    [K in StrategyType]: {
        id: string;
        type: K;
        params: StrategyParamsByType[K];
        isExpanded: boolean;
    };
}[StrategyType];

export type StrategyParams = StrategyInstance['params'];
export type StrategySummaryTag = Pick<TagView, 'tag_id' | 'name'>;

export const STRATEGY_OPTIONS: { type: StrategyType; label: string }[] = [
    { type: 'diversity', label: 'Diversity' },
    { type: 'typicality', label: 'Typicality' },
    { type: 'similarity', label: 'Similarity' },
    { type: 'metadata_weighting', label: 'Metadata Weighting' },
    { type: 'class_balancing', label: 'Class Balancing' }
];

export const STRATEGY_LABELS: Record<StrategyType, string> = Object.fromEntries(
    STRATEGY_OPTIONS.map((strategy) => [strategy.type, strategy.label])
) as Record<StrategyType, string>;

export const STRATEGY_DEFAULTS: { [K in StrategyType]: StrategyParamsByType[K] } = {
    diversity: { embedding_model_name: '', strength: 1 },
    typicality: { strength: 1 },
    similarity: { query_tag_id: '', embedding_model_name: '', strength: 1 },
    metadata_weighting: { metadata_key: '', strength: 1 },
    class_balancing: { target_distribution: [], strength: 1 }
};

function createId(): string {
    return crypto.randomUUID();
}

function cloneClassBalancingRows(rows: ClassBalancingTargetRow[]): ClassBalancingTargetRow[] {
    return rows.map((row) => ({ ...row }));
}

export function cloneStrategyParams<T extends StrategyType>(
    type: T,
    params: StrategyParamsByType[T]
): StrategyParamsByType[T] {
    if (type === 'class_balancing') {
        return {
            ...params,
            target_distribution: cloneClassBalancingRows(
                (params as ClassBalancingParams).target_distribution
            )
        } as StrategyParamsByType[T];
    }

    return { ...params };
}

export function createStrategyInstance(type: StrategyType): StrategyInstance {
    return {
        id: createId(),
        type,
        params: cloneStrategyParams(type, STRATEGY_DEFAULTS[type]),
        isExpanded: true
    } as StrategyInstance;
}

function getTagName(tagId: string, tags: StrategySummaryTag[]): string | null {
    return tags.find((tag) => tag.tag_id === tagId)?.name ?? null;
}

function formatStrength(strength: number): string {
    return `strength ${strength}`;
}

export function getStrategyParameterSummary(
    instance: StrategyInstance,
    tags: StrategySummaryTag[] = []
): string {
    const parts: string[] = [];

    if (instance.type === 'diversity') {
        if (instance.params.embedding_model_name.trim()) {
            parts.push(instance.params.embedding_model_name.trim());
        }
    }

    if (instance.type === 'typicality') {
        if (instance.params.strength !== 1) {
            parts.push(formatStrength(instance.params.strength));
        }
    }

    if (instance.type === 'similarity') {
        const tagName = getTagName(instance.params.query_tag_id, tags);
        if (tagName) {
            parts.push(`tag: ${tagName}`);
        }
        if (instance.params.embedding_model_name.trim()) {
            parts.push(instance.params.embedding_model_name.trim());
        }
    }

    if (instance.type === 'metadata_weighting') {
        if (instance.params.metadata_key.trim()) {
            parts.push(instance.params.metadata_key.trim());
        }
    }

    if (instance.type === 'class_balancing') {
        const classCount = instance.params.target_distribution.length;
        if (classCount > 0) {
            parts.push(`${classCount} classes`);
        }
    }

    if (
        'strength' in instance.params &&
        instance.params.strength !== 1 &&
        instance.type !== 'typicality'
    ) {
        parts.push(formatStrength(instance.params.strength));
    }

    return parts.join(', ');
}

export function getStrategyDisplayLabel(
    instance: StrategyInstance,
    tags: StrategySummaryTag[] = []
): string {
    const summary = getStrategyParameterSummary(instance, tags);
    if (!summary) {
        return STRATEGY_LABELS[instance.type];
    }

    return `${STRATEGY_LABELS[instance.type]} · ${summary}`;
}

function isPositiveNumber(value: number): boolean {
    return Number.isFinite(value) && value > 0;
}

export function isStrategyInstanceValid(instance: StrategyInstance): boolean {
    if (!isPositiveNumber(instance.params.strength)) {
        return false;
    }

    if (instance.type === 'similarity') {
        return instance.params.query_tag_id.trim().length > 0;
    }

    if (instance.type === 'metadata_weighting') {
        return instance.params.metadata_key.trim().length > 0;
    }

    if (instance.type === 'class_balancing') {
        return (
            instance.params.target_distribution.length > 0 &&
            instance.params.target_distribution.every(
                (row) => row.class_name.trim().length > 0 && isPositiveNumber(row.weight)
            )
        );
    }

    return true;
}

function updateStrategyInstance(
    instance: StrategyInstance,
    params: Partial<StrategyParams>
): StrategyInstance {
    if (instance.type === 'diversity') {
        return {
            ...instance,
            params: { ...instance.params, ...(params as Partial<DiversityParams>) }
        };
    }
    if (instance.type === 'typicality') {
        return {
            ...instance,
            params: { ...instance.params, ...(params as Partial<TypicalityParams>) }
        };
    }
    if (instance.type === 'similarity') {
        return {
            ...instance,
            params: { ...instance.params, ...(params as Partial<SimilarityParams>) }
        };
    }
    if (instance.type === 'metadata_weighting') {
        return {
            ...instance,
            params: { ...instance.params, ...(params as Partial<MetadataWeightingParams>) }
        };
    }

    return {
        ...instance,
        params: { ...instance.params, ...(params as Partial<ClassBalancingParams>) }
    };
}

export function useStrategyBuilder() {
    const instances = writable<StrategyInstance[]>([]);

    function addStrategy(type: StrategyType) {
        instances.update((currentInstances) => [...currentInstances, createStrategyInstance(type)]);
    }

    function removeStrategy(id: string) {
        instances.update((currentInstances) =>
            currentInstances.filter((instance) => instance.id !== id)
        );
    }

    function duplicateStrategy(id: string) {
        instances.update((currentInstances) => {
            const index = currentInstances.findIndex((instance) => instance.id === id);
            if (index < 0) {
                return currentInstances;
            }

            const source = currentInstances[index];
            const copy: StrategyInstance = {
                ...source,
                id: createId(),
                params: cloneStrategyParams(source.type, source.params),
                isExpanded: true
            } as StrategyInstance;

            return [
                ...currentInstances.slice(0, index + 1),
                copy,
                ...currentInstances.slice(index + 1)
            ];
        });
    }

    function updateParams(id: string, params: Partial<StrategyParams>) {
        instances.update((currentInstances) =>
            currentInstances.map((instance) =>
                instance.id === id ? updateStrategyInstance(instance, params) : instance
            )
        );
    }

    function toggleExpand(id: string) {
        instances.update((currentInstances) =>
            currentInstances.map((instance) =>
                instance.id === id ? { ...instance, isExpanded: !instance.isExpanded } : instance
            )
        );
    }

    function resetStrategies() {
        instances.set([]);
    }

    return {
        instances,
        addStrategy,
        removeStrategy,
        duplicateStrategy,
        updateParams,
        toggleExpand,
        resetStrategies
    };
}
