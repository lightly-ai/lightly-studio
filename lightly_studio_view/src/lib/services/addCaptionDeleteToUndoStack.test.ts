import { describe, it, expect, vi } from 'vitest';
import {
    addCaptionDeleteToUndoStack,
    CAPTION_DELETE_GROUP_ID
} from './addCaptionDeleteToUndoStack';
import type { CreateCaptionResponse } from '$lib/api/lightly_studio_local';
import type { ReversibleAction } from '$lib/hooks/useReversibleActions';

describe('addCaptionDeleteToUndoStack', () => {
    it('should add a reversible action to the undo stack', () => {
        const addReversibleAction = vi.fn();
        const createCaption = vi.fn().mockResolvedValue({} as CreateCaptionResponse);
        const refetch = vi.fn();

        addCaptionDeleteToUndoStack({
            text: 'A caption about a dog',
            parentSampleId: 'sample-123',
            addReversibleAction,
            createCaption,
            refetch
        });

        expect(addReversibleAction).toHaveBeenCalledTimes(1);
        const action = addReversibleAction.mock.calls[0][0] as ReversibleAction;
        expect(action.id).toContain('caption-delete-sample-123');
        expect(action.description).toBe('Undo delete caption');
        expect(action.groupId).toBe(CAPTION_DELETE_GROUP_ID);
    });

    it('should call createCaption with the original text and parentSampleId when execute is called', async () => {
        const addReversibleAction = vi.fn();
        const createCaption = vi.fn().mockResolvedValue({} as CreateCaptionResponse);
        const refetch = vi.fn();

        addCaptionDeleteToUndoStack({
            text: 'A caption about a dog',
            parentSampleId: 'sample-123',
            addReversibleAction,
            createCaption,
            refetch
        });

        const action = addReversibleAction.mock.calls[0][0] as ReversibleAction;
        await action.execute();

        expect(createCaption).toHaveBeenCalledWith({
            parent_sample_id: 'sample-123',
            text: 'A caption about a dog'
        });
        expect(refetch).toHaveBeenCalled();
    });

    it('should handle an empty caption text', async () => {
        const addReversibleAction = vi.fn();
        const createCaption = vi.fn().mockResolvedValue({} as CreateCaptionResponse);
        const refetch = vi.fn();

        addCaptionDeleteToUndoStack({
            text: '',
            parentSampleId: 'sample-123',
            addReversibleAction,
            createCaption,
            refetch
        });

        const action = addReversibleAction.mock.calls[0][0] as ReversibleAction;
        await action.execute();

        expect(createCaption).toHaveBeenCalledWith({
            parent_sample_id: 'sample-123',
            text: ''
        });
        expect(refetch).toHaveBeenCalled();
    });
});
