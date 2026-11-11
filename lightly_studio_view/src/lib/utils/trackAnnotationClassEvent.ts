import { page } from '$app/state';
// Imported by its own path, so tests that mock the $lib/hooks barrel still work.
import { usePostHog } from '$lib/hooks/usePostHog';

// Tracks how users manage annotation classes. Sends ids and counts, never class names.
export const trackAnnotationClassEvent = (
    action: 'create_clicked' | 'rename_submitted' | 'delete_clicked',
    properties: Record<string, unknown> = {}
) =>
    usePostHog().trackEvent(`annotation_class_${action}`, {
        dataset_id: page.params.dataset_id,
        collection_id: page.params.collection_id,
        ...properties
    });

// For the "Create: <name>" item in class pickers. The class is saved with the annotation.
export const trackClassCreatedInPicker = () =>
    trackAnnotationClassEvent('create_clicked', { source: 'class_picker' });
