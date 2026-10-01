import { describe, expect, it, vi } from 'vitest';
import { useCaption } from './useCaption';

const { mutateAsync } = vi.hoisted(() => ({ mutateAsync: vi.fn() }));
vi.mock('@tanstack/svelte-query', () => ({ createMutation: () => ({ mutateAsync }) }));
vi.mock('svelte-sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() } }));

const { toast } = await import('svelte-sonner');

describe('useCaption', () => {
    it('sends the new text as a structured update body', async () => {
        const onUpdate = vi.fn();
        const { updateCaptionText } = useCaption({ sampleId: 'sample-1', onUpdate });

        await updateCaptionText('new text');

        expect(mutateAsync).toHaveBeenCalledWith({
            path: { sample_id: 'sample-1' },
            body: { text: 'new text' }
        });
        expect(onUpdate).toHaveBeenCalledWith();
    });

    it('reports a failed update as an error toast', async () => {
        mutateAsync.mockRejectedValueOnce(new Error('boom'));
        const { updateCaptionText } = useCaption({ sampleId: 'sample-1' });

        await updateCaptionText('new text');

        expect(toast.error).toHaveBeenCalledWith('Failed to update caption: boom');
    });
});
