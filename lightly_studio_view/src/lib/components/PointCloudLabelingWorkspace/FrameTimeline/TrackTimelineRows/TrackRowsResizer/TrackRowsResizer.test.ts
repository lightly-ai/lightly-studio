import { beforeEach, describe, expect, it } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import TrackRowsResizer from './TrackRowsResizer.svelte';
import {
    DEFAULT_TRACK_ROWS_HEIGHT,
    MAX_TRACK_ROWS_HEIGHT,
    MIN_TRACK_ROWS_HEIGHT,
    useTrackRowsHeight
} from './useTrackRowsHeight.svelte';

// jsdom has no PointerEvent, so pointer events are sent as mouse events with a pointer name.
const pointer = (element: HTMLElement, type: string, clientY = 0) =>
    fireEvent(element, new MouseEvent(type, { bubbles: true, clientY }));

describe('TrackRowsResizer', () => {
    beforeEach(() => localStorage.clear());

    it('grows the rows when dragged up and shrinks them when dragged down', async () => {
        const rowsHeight = useTrackRowsHeight();
        render(TrackRowsResizer, { props: { rowsHeight } });
        const handle = screen.getByTestId('track-rows-resizer');

        await pointer(handle, 'pointerdown', 500);
        await pointer(handle, 'pointermove', 440);
        expect(rowsHeight.height).toBe(DEFAULT_TRACK_ROWS_HEIGHT + 60);
        await pointer(handle, 'pointermove', 520);
        expect(rowsHeight.height).toBe(DEFAULT_TRACK_ROWS_HEIGHT - 20);
        await pointer(handle, 'pointerup');
        await pointer(handle, 'pointermove', 0);

        expect(rowsHeight.height).toBe(DEFAULT_TRACK_ROWS_HEIGHT - 20);
    });

    it('keeps the height within its limits and remembers it', async () => {
        const rowsHeight = useTrackRowsHeight();
        rowsHeight.setHeight(99999);
        expect(rowsHeight.height).toBe(MAX_TRACK_ROWS_HEIGHT);
        rowsHeight.setHeight(1);
        expect(rowsHeight.height).toBe(MIN_TRACK_ROWS_HEIGHT);

        rowsHeight.setHeight(222);
        expect(useTrackRowsHeight().height).toBe(222);
    });

    it('resizes with the arrow keys', async () => {
        const rowsHeight = useTrackRowsHeight();
        render(TrackRowsResizer, { props: { rowsHeight } });

        await fireEvent.keyDown(screen.getByTestId('track-rows-resizer'), { key: 'ArrowUp' });

        expect(rowsHeight.height).toBeGreaterThan(DEFAULT_TRACK_ROWS_HEIGHT);
    });

    it('shrinks right away when the rows are shorter than the limit', async () => {
        const rowsHeight = useTrackRowsHeight();
        render(TrackRowsResizer, { props: { rowsHeight, getRenderedHeight: () => 100 } });
        const handle = screen.getByTestId('track-rows-resizer');

        await pointer(handle, 'pointerdown', 500);
        await pointer(handle, 'pointermove', 520);

        expect(rowsHeight.height).toBe(80);
    });
});
