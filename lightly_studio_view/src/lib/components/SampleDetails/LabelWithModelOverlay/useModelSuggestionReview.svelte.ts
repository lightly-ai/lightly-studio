import type { ModelAnnotationPreview } from '$lib/api/lightly_studio_local';

export interface ModelSuggestion {
    id: number;
    preview: ModelAnnotationPreview;
    included: boolean;
}

export const useModelSuggestionReview = () => {
    let suggestions = $state<ModelSuggestion[]>([]);
    let focusedId = $state<number | null>(null);
    let nextId = 0;

    const replace = (predictions: ModelAnnotationPreview[]) => {
        suggestions = predictions.map((preview) => ({ id: nextId++, preview, included: true }));
        focusedId = null;
    };

    const remove = (preview: ModelAnnotationPreview) => {
        suggestions = suggestions.filter((suggestion) => suggestion.preview !== preview);
        if (!suggestions.some((suggestion) => suggestion.id === focusedId)) focusedId = null;
    };

    return {
        get suggestions() {
            return suggestions;
        },
        get focusedId() {
            return focusedId;
        },
        get focusedSuggestion() {
            return suggestions.find((suggestion) => suggestion.id === focusedId);
        },
        get includedSuggestions() {
            return suggestions.filter((suggestion) => suggestion.included);
        },
        focus: (id: number | null) => {
            focusedId = id;
        },
        setIncluded: (id: number, included: boolean) => {
            const suggestion = suggestions.find((suggestion) => suggestion.id === id);
            if (suggestion) suggestion.included = included;
        },
        selectAll: () => {
            suggestions.forEach((suggestion) => {
                suggestion.included = true;
            });
        },
        selectNone: () => {
            suggestions.forEach((suggestion) => {
                suggestion.included = false;
            });
        },
        changeClass: (className: string) => {
            const suggestion = suggestions.find((suggestion) => suggestion.id === focusedId);
            if (suggestion) suggestion.preview.class_name = className;
        },
        replace,
        remove
    };
};
