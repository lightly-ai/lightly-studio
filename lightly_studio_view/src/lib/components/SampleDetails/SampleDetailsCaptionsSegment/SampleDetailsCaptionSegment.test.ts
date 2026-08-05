import { fireEvent, render, screen } from '@testing-library/svelte';
import { writable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { CaptionView } from '$lib/api/lightly_studio_local';
import { CAPTION_SEGMENT_MATCH_SCORE_KEY } from '$lib/constants';
import SampleDetailsCaptionSegment from './SampleDetailsCaptionSegment.svelte';

const { createCaptionMock } = vi.hoisted(() => ({
    createCaptionMock: vi.fn()
}));

vi.mock('$app/state', () => ({
    page: {
        params: {
            dataset_id: 'dataset-1'
        },
        data: {
            globalStorage: {
                isEditingMode: writable(true)
            }
        }
    }
}));

vi.mock('$lib/hooks/useGlobalStorage', () => ({
    useGlobalStorage: () => ({
        isEditingMode: writable(true),
        addReversibleAction: vi.fn()
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

vi.mock('$lib/hooks/useCaption/useCaption', () => ({
    useCaption: () => ({
        updateCaptionText: vi.fn()
    })
}));

vi.mock('svelte-sonner', () => ({
    toast: {
        success: vi.fn(),
        error: vi.fn()
    }
}));

function makeCaption(overrides: Partial<CaptionView> & { score?: number }): CaptionView {
    const { score, ...rest } = overrides;
    return {
        sample_id: 'cap-1',
        parent_sample_id: 'sample-1',
        text: 'Caption text',
        temporal_span_details: { start_time_s: 1, end_time_s: 3 },
        metadata_dict:
            score === undefined
                ? { data: {} }
                : { data: { [CAPTION_SEGMENT_MATCH_SCORE_KEY]: score } },
        ...rest
    } as CaptionView;
}

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

    it('shows match score filter chips and sorts lowest scores first', () => {
        render(SampleDetailsCaptionSegment, {
            props: {
                captions: [
                    makeCaption({ sample_id: 'high', text: 'High match', score: 0.9 }),
                    makeCaption({ sample_id: 'low', text: 'Low match', score: 0.1 })
                ],
                sampleId: 'sample-1',
                refetch: vi.fn()
            }
        });

        expect(screen.getByTestId('match-score-filter-chips')).toBeInTheDocument();
        const rows = screen.getAllByTestId('caption-field-row');
        expect(rows[0]).toHaveAttribute('data-caption-id', 'low');
        expect(rows[1]).toHaveAttribute('data-caption-id', 'high');
    });

    it('filters captions by match band', async () => {
        render(SampleDetailsCaptionSegment, {
            props: {
                captions: [
                    makeCaption({ sample_id: 'high', text: 'High match', score: 0.9 }),
                    makeCaption({ sample_id: 'low', text: 'Low match', score: 0.1 })
                ],
                sampleId: 'sample-1',
                refetch: vi.fn()
            }
        });

        await fireEvent.click(screen.getByTestId('match-score-filter-low'));

        expect(screen.getAllByTestId('caption-field-row')).toHaveLength(1);
        expect(screen.getByTestId('caption-field-row')).toHaveAttribute('data-caption-id', 'low');
    });

    it('highlights the caption under the playhead and calls onSelectCaption', async () => {
        const onSelectCaption = vi.fn();
        render(SampleDetailsCaptionSegment, {
            props: {
                captions: [
                    makeCaption({
                        sample_id: 'cap-a',
                        temporal_span_details: { start_time_s: 0, end_time_s: 2 },
                        score: 0.2
                    }),
                    makeCaption({
                        sample_id: 'cap-b',
                        temporal_span_details: { start_time_s: 2, end_time_s: 4 },
                        score: 0.8
                    })
                ],
                sampleId: 'sample-1',
                refetch: vi.fn(),
                currentTimeS: 2.5,
                onSelectCaption
            }
        });

        const rows = screen.getAllByTestId('caption-field-row');
        const active = rows.find((row) => row.getAttribute('data-active') === 'true');
        expect(active).toHaveAttribute('data-caption-id', 'cap-b');

        await fireEvent.click(rows[0]);
        expect(onSelectCaption).toHaveBeenCalledWith('cap-a');
    });
});
