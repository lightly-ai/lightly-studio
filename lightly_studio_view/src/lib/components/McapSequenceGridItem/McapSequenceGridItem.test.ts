import { describe, it, expect, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/svelte';
import { tick } from 'svelte';
import McapSequenceGridItem from './McapSequenceGridItem.svelte';

describe('McapSequenceGridItem', () => {
    const defaultProps = {
        sampleCount: 1,
        width: 200,
        height: 200,
        sequenceFrame: null
    };

    it('renders a visible placeholder when the sequence has no preview', () => {
        const { getByText } = render(McapSequenceGridItem, { props: defaultProps });

        expect(getByText('MCAP sequence')).toBeInTheDocument();
    });

    it('shows an additional-frame badge only for multi-frame sequences', () => {
        const { queryByTestId } = render(McapSequenceGridItem, {
            props: defaultProps
        });

        expect(queryByTestId('mcap-sequence-frame-count')).not.toBeInTheDocument();

        const { getByTestId } = render(McapSequenceGridItem, {
            props: { ...defaultProps, sampleCount: 5 }
        });

        expect(getByTestId('mcap-sequence-frame-count').textContent?.trim()).toBe('+4');
    });

    it('renders an img with the camera-frame URL when sequenceFrame is provided', () => {
        const sequenceFrame = {
            dataset_id: 'ds-recording',
            recording_id: 'rec-abc',
            channel_id: 2,
            keyframe_log_time_ns: '90'
        };

        const { getByRole } = render(McapSequenceGridItem, {
            props: { ...defaultProps, sequenceFrame }
        });

        const img = getByRole('img') as HTMLImageElement;
        expect(img.src).toContain('datasets/ds-recording/recordings/rec-abc/camera-frame');
        expect(img.src).toContain('channel_id=2');
        expect(img.src).toContain('keyframe_timestamp_ns=90');
        expect(img.src).toContain('w=200');
        expect(img.src).toContain('h=200');
    });

    it('renders an img when frameUrl changes after a prior URL failed', async () => {
        vi.useFakeTimers();

        const sequenceFrame = {
            dataset_id: 'ds-recording',
            recording_id: 'rec-abc',
            channel_id: 2,
            keyframe_log_time_ns: '90'
        };

        const { getByRole, queryByRole, rerender } = render(McapSequenceGridItem, {
            props: { ...defaultProps, sequenceFrame }
        });

        fireEvent.error(getByRole('img'));
        await tick();

        expect(queryByRole('img')).not.toBeInTheDocument();

        await rerender({
            ...defaultProps,
            sequenceFrame: { ...sequenceFrame, keyframe_log_time_ns: '100' }
        });

        vi.runAllTimers();
        await tick();

        expect(getByRole('img')).toBeInTheDocument();

        vi.useRealTimers();
    });
});
