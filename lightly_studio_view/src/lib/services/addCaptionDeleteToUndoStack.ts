import type { CaptionCreateInput, CreateCaptionResponse } from '$lib/api/lightly_studio_local';
import type { ReversibleAction } from '$lib/hooks/useReversibleActions';

export const CAPTION_DELETE_GROUP_ID = 'caption-delete';

export const addCaptionDeleteToUndoStack = ({
    text,
    parentSampleId,
    addReversibleAction,
    createCaption,
    refetch
}: {
    text: string;
    parentSampleId: string;
    addReversibleAction: (action: ReversibleAction) => void;
    createCaption: (input: CaptionCreateInput) => Promise<CreateCaptionResponse>;
    refetch: () => void;
}) => {
    const execute = async () => {
        await createCaption({ parent_sample_id: parentSampleId, text });
        refetch();
    };

    addReversibleAction({
        id: `caption-delete-${parentSampleId}-${Date.now()}`,
        description: 'Undo delete caption',
        execute,
        timestamp: new Date(),
        groupId: CAPTION_DELETE_GROUP_ID
    });
};
