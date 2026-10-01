import { type UpdateCaptionData } from '$lib/api/lightly_studio_local';
import { updateCaptionMutation } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createMutation } from '@tanstack/svelte-query';
import { toast } from 'svelte-sonner';

export const useCaption = ({ sampleId, onUpdate }: { sampleId: string; onUpdate?: () => void }) => {
    const captionMutation = createMutation(() => updateCaptionMutation());

    const mutateCaptionText = async (text: string): Promise<void> => {
        await captionMutation.mutateAsync({
            path: {
                sample_id: sampleId
            } as UpdateCaptionData['path'],
            body: { text }
        });
    };

    const updateCaptionText = async (text: string) => {
        try {
            await mutateCaptionText(text);
            toast.success('Caption updated successfully');
            onUpdate?.();
        } catch (error: unknown) {
            toast.error('Failed to update caption: ' + (error as Error).message);
        }
    };
    return {
        updateCaptionText
    };
};
