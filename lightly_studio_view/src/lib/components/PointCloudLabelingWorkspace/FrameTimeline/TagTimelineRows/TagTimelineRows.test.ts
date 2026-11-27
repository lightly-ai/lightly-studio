import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import TagTimelineRows from './TagTimelineRows.svelte';

const ticks = [0, 1, 2, 3].map((seq_number) => ({ seq_number, timestamp_ns: null }));
const tags = [
    { tag_id: 'tag-1', name: 'occluded', seq_numbers: [0, 1, 3] },
    { tag_id: 'tag-2', name: 'night', seq_numbers: [2] }
];

describe('TagTimelineRows', () => {
    it('draws one row per tag with a bar per run of tagged frames', () => {
        render(TagTimelineRows, { props: { ticks, tags, onSelectTick: vi.fn() } });

        expect(screen.getAllByTestId('tag-row-label').map((label) => label.textContent)).toEqual([
            'occluded',
            'night'
        ]);
        expect(screen.getAllByTitle(/ · Frames? /).map((bar) => bar.getAttribute('title'))).toEqual(
            ['occluded · Frames 1–2', 'occluded · Frame 4', 'night · Frame 3']
        );
    });

    it('selects the first frame of the clicked bar', async () => {
        const onSelectTick = vi.fn();
        render(TagTimelineRows, { props: { ticks, tags, onSelectTick } });

        await fireEvent.click(screen.getByTitle('occluded · Frame 4'));

        expect(onSelectTick).toHaveBeenCalledWith(3);
    });

    it('renders no rows without tags', () => {
        render(TagTimelineRows, { props: { ticks, tags: [], onSelectTick: vi.fn() } });

        expect(screen.queryByTestId('frame-tag-rows')).toBeNull();
    });

    it('keeps the tag names at the left edge while the timeline scrolls', () => {
        render(TagTimelineRows, { props: { ticks, tags, onSelectTick: vi.fn() } });

        // The rows scroll with the whole timeline, so they have no scroll area of their own.
        expect(screen.getByTestId('frame-tag-rows')).not.toHaveClass('overflow-y-auto');
        for (const label of screen.getAllByTestId('tag-row-label')) {
            expect(label).toHaveClass('sticky', 'left-3');
        }
    });
});
