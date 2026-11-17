import type { ModelAnnotationPreview } from '$lib/api/lightly_studio_local';

export interface ModelSuggestion {
    id: number;
    preview: ModelAnnotationPreview;
    box: ModelAnnotationPreview['bbox'];
    status: 'pending' | 'accepted' | 'rejected';
}

export const getSuggestionPreview = (suggestion: ModelSuggestion, saveAs: 'mask' | 'box') => ({
    ...suggestion.preview,
    bbox:
        saveAs === 'box' || !suggestion.preview.segmentation_mask
            ? suggestion.box
            : suggestion.preview.bbox
});

export const useModelSuggestionReview = () => {
    let suggestions = $state<ModelSuggestion[]>([]);
    let focusedId = $state<number | null>(null);
    let nextId = 0;
    let hideAccepted = $state(false);

    const replace = (predictions: ModelAnnotationPreview[]) => {
        suggestions = predictions.map((preview) => ({
            id: nextId++,
            preview,
            box: { ...preview.bbox },
            status: 'pending'
        }));
        focusedId = null;
        hideAccepted = false;
    };

    const remove = (preview: ModelAnnotationPreview) => {
        suggestions = suggestions.filter((suggestion) => suggestion.preview !== preview);
        if (!suggestions.some((suggestion) => suggestion.id === focusedId)) focusedId = null;
    };

    const setStatus = (id: number, status: ModelSuggestion['status']) => {
        const suggestion = suggestions.find((suggestion) => suggestion.id === id);
        if (suggestion) suggestion.status = status;
    };

    return {
        get hideAccepted() {
            return hideAccepted;
        },
        setHideAccepted: (value: boolean) => {
            hideAccepted = value;
        },
        isVisible: (suggestion: ModelSuggestion) =>
            suggestion.status !== 'rejected' && !(hideAccepted && suggestion.status === 'accepted'),
        undo: (id: number) => setStatus(id, 'pending'),
        get suggestions() {
            return suggestions;
        },
        get focusedId() {
            return focusedId;
        },
        get focusedSuggestion() {
            return suggestions.find((suggestion) => suggestion.id === focusedId);
        },
        get acceptedSuggestions() {
            return suggestions.filter((suggestion) => suggestion.status === 'accepted');
        },
        get pendingCount() {
            return suggestions.filter((suggestion) => suggestion.status === 'pending').length;
        },
        get hasUnsavedSuggestions() {
            return suggestions.some((suggestion) => suggestion.status !== 'rejected');
        },
        focus: (id: number | null) => {
            focusedId = id;
        },
        accept: (id: number) => setStatus(id, 'accepted'),
        reject: (id: number) => setStatus(id, 'rejected'),
        acceptAll: () => {
            suggestions.forEach((suggestion) => {
                suggestion.status = 'accepted';
            });
        },
        changeClass: (id: number, className: string) => {
            const suggestion = suggestions.find((suggestion) => suggestion.id === id);
            if (suggestion) suggestion.preview.class_name = className;
        },
        updateBox: (
            id: number,
            box: ModelAnnotationPreview['bbox'],
            image: { width: number; height: number }
        ) => {
            const suggestion = suggestions.find((suggestion) => suggestion.id === id);
            if (!suggestion) return;
            const x = Math.max(0, Math.min(Math.round(box.x), image.width - 1));
            const y = Math.max(0, Math.min(Math.round(box.y), image.height - 1));
            suggestion.box = {
                x,
                y,
                width: Math.max(1, Math.min(Math.round(box.width), image.width - x)),
                height: Math.max(1, Math.min(Math.round(box.height), image.height - y))
            };
        },
        replace,
        remove
    };
};
