import { render, screen, fireEvent } from '@testing-library/svelte';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { GRID_IMAGE_SEARCH_DROP_EVENT } from '$lib/components/GridItem/GridItem.constants';
import UseGridItemDragTestWrapper from './useGridItemDragTestWrapper.test.svelte';

const dragData = { url: '/api/images/sample/1', fileName: 'sample.jpg' };

function ptr(
    type: string,
    options: { clientX: number; clientY: number; pointerId?: number; button?: number }
): Event {
    const event = new Event(type, { bubbles: true }) as PointerEvent;
    Object.defineProperties(event, {
        button: { value: options.button ?? 0 },
        pointerId: { value: options.pointerId ?? 1 },
        clientX: { value: options.clientX },
        clientY: { value: options.clientY }
    });
    return event;
}

beforeEach(() => {
    Object.defineProperty(document, 'elementFromPoint', {
        configurable: true,
        value: vi.fn(() => null)
    });
});

afterEach(() => {
    document.body.style.cursor = '';
    vi.restoreAllMocks();
});

describe('useGridItemDrag', () => {
    it('keeps pointer movement below the drag threshold idle', async () => {
        const onDrop = vi.fn();
        window.addEventListener(GRID_IMAGE_SEARCH_DROP_EVENT, onDrop);

        render(UseGridItemDragTestWrapper, { props: { dragData } });
        const host = screen.getByTestId('drag-host');
        const dropTarget = document.createElement('div');
        dropTarget.setAttribute('data-grid-search-drop-target', '');
        vi.mocked(document.elementFromPoint).mockReturnValue(dropTarget);

        await fireEvent(host, ptr('pointerdown', { clientX: 0, clientY: 0 }));
        await fireEvent(host, ptr('pointermove', { clientX: 3, clientY: 4 }));
        await fireEvent(host, ptr('pointerup', { clientX: 3, clientY: 4 }));

        expect(screen.queryByTestId('is-dragging')).not.toBeInTheDocument();
        expect(screen.queryByTestId('drag-preview')).not.toBeInTheDocument();
        expect(document.body.style.cursor).toBe('');
        expect(onDrop).not.toHaveBeenCalled();

        window.removeEventListener(GRID_IMAGE_SEARCH_DROP_EVENT, onDrop);
    });

    it('starts dragging after threshold movement and resets on pointer up', async () => {
        render(UseGridItemDragTestWrapper, { props: { dragData } });
        const host = screen.getByTestId('drag-host');

        await fireEvent(host, ptr('pointerdown', { clientX: 10, clientY: 10 }));
        await fireEvent(host, ptr('pointermove', { clientX: 20, clientY: 10 }));

        expect(screen.getByTestId('is-dragging')).toBeInTheDocument();
        expect(screen.getByTestId('drag-preview')).toBeInTheDocument();
        expect(document.body.style.cursor).toBe('grabbing');

        await fireEvent(host, ptr('pointerup', { clientX: 20, clientY: 10 }));

        expect(screen.queryByTestId('is-dragging')).not.toBeInTheDocument();
        expect(screen.queryByTestId('drag-preview')).not.toBeInTheDocument();
        expect(document.body.style.cursor).toBe('');
    });

    it('dispatches drop data when released over a drop target', async () => {
        const onDrop = vi.fn();
        window.addEventListener(GRID_IMAGE_SEARCH_DROP_EVENT, onDrop);

        render(UseGridItemDragTestWrapper, { props: { dragData } });
        const host = screen.getByTestId('drag-host');

        const dropTarget = document.createElement('div');
        dropTarget.setAttribute('data-grid-search-drop-target', '');
        vi.mocked(document.elementFromPoint).mockReturnValue(dropTarget);

        await fireEvent(host, ptr('pointerdown', { clientX: 0, clientY: 0 }));
        await fireEvent(host, ptr('pointermove', { clientX: 20, clientY: 0 }));
        await fireEvent(host, ptr('pointerup', { clientX: 20, clientY: 0 }));

        expect(onDrop).toHaveBeenCalledOnce();
        expect(onDrop.mock.calls[0][0].detail).toEqual(dragData);

        window.removeEventListener(GRID_IMAGE_SEARCH_DROP_EVENT, onDrop);
    });
});
