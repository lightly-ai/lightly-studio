import { fireEvent, render, screen } from '@testing-library/svelte';
import { writable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import SampleDetailsCaptionSegment from './SampleDetailsCaptionSegment.svelte';

const { createCaptionMock } = vi.hoisted(() => ({
    createCaptionMock: vi.fn()
}));

vi.mock('$app/state', () => ({
    page: {
        params: {
            dataset_id: 'dataset-1'
        }
    }
}));

vi.mock('$lib/hooks/useGlobalStorage', () => ({
    useGlobalStorage: () => ({
        isEditingMode: writable(true)
    })
}));

vi.mock('$lib/hooks/useDeleteCaption/useDeleteCaption', () => ({
    useDeleteCaption: () => ({
        deleteCaption: vi.fn()
    })
}));

vi.mock('$lib/hooks/useCreateCaption/useCreateCaption', () => ({
    useCreateCaption: () => ({
        createCaption: createCaptionMock
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

describe('SampleDetailsCaptionSegment', () => {
    beforeEach(() => {
        createCaptionMock.mockReset();
        createCaptionMock.mockResolvedValue({});
    });

    it('does not create a caption immediately when add button is clicked', async () => {
        render(SampleDetailsCaptionSegment, {
            props: {
                captions: [],
                sampleId: 'sample-1',
                refetch: vi.fn()
            }
        });

        await fireEvent.click(screen.getByTestId('add-caption-button'));

        expect(createCaptionMock).not.toHaveBeenCalled();
        expect(screen.getByTestId('new-caption-input')).toBeInTheDocument();
        expect(screen.getByTestId('new-caption-input')).toHaveFocus();
    });
});
