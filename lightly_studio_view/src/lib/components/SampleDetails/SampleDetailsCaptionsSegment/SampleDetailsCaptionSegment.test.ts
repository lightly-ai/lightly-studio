import { fireEvent, render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import SampleDetailsCaptionSegment from './SampleDetailsCaptionSegment.svelte';

const mocks = vi.hoisted(() => ({
    createCaption: vi.fn(),
    isEditingMode: undefined as unknown as { set: (value: boolean) => void },
    userRole: 'labeler' as string | undefined
}));

vi.mock('$app/state', () => ({
    page: {
        params: {
            dataset_id: 'dataset-1'
        }
    }
}));

vi.mock('$lib/hooks/useAuth/useAuth', () => ({
    default: () => ({ user: mocks.userRole ? { role: mocks.userRole } : undefined })
}));

vi.mock('$lib/hooks/useGlobalStorage', async () => {
    const { writable } = await import('svelte/store');
    const isEditingMode = writable(false);
    mocks.isEditingMode = isEditingMode;
    return {
        useGlobalStorage: () => ({
            isEditingMode,
            addReversibleAction: vi.fn()
        })
    };
});

vi.mock('$lib/hooks/useDeleteCaption/useDeleteCaption', () => ({
    useDeleteCaption: () => ({
        deleteCaption: vi.fn()
    })
}));

vi.mock('$lib/hooks/useCreateCaption/useCreateCaption', () => ({
    useCreateCaption: () => ({
        createCaption: mocks.createCaption
    })
}));

vi.mock('$lib/hooks/useCollection/useCollection', () => ({
    useCollectionWithChildren: () => ({
        refetch: vi.fn()
    })
}));

vi.mock('svelte-sonner', () => ({
    toast: {
        success: vi.fn(),
        error: vi.fn()
    }
}));

const defaultProps = {
    captions: [],
    sampleId: 'sample-1',
    refetch: vi.fn()
};

describe('SampleDetailsCaptionSegment', () => {
    beforeEach(() => {
        mocks.createCaption.mockReset();
        mocks.createCaption.mockResolvedValue({});
        mocks.userRole = 'labeler';
        mocks.isEditingMode.set(false);
    });

    it('does not create a caption immediately when add button is clicked', async () => {
        mocks.isEditingMode.set(true);
        render(SampleDetailsCaptionSegment, { props: defaultProps });

        await fireEvent.click(screen.getByTestId('add-caption-button'));

        expect(mocks.createCaption).not.toHaveBeenCalled();
        expect(screen.getByTestId('new-caption-input')).toBeInTheDocument();
        expect(screen.getByTestId('new-caption-input')).toHaveFocus();
    });

    it('shows edit guidance for users who can edit when there are no captions', () => {
        mocks.userRole = 'labeler';
        render(SampleDetailsCaptionSegment, { props: defaultProps });

        expect(screen.getByTestId('empty-state-message')).toHaveTextContent(
            'No captions. Click Edit annotations to add one.'
        );
    });

    it('shows plain "No captions." without edit guidance for viewer role', () => {
        mocks.userRole = 'viewer';
        render(SampleDetailsCaptionSegment, { props: defaultProps });

        expect(screen.getByTestId('empty-state-message')).toHaveTextContent('No captions.');
    });
});
