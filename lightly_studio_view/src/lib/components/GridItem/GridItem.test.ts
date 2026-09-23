import { describe, it, expect, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import GridItemTestWrapper from './GridItemTestWrapper.test.svelte';

describe('GridItem', () => {
    const defaultProps = {
        content: 'Sample content'
    };

    function createPointerEvent(
        type: string,
        options: { button?: number; pointerId?: number; clientX: number; clientY: number }
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

    it('renders with default dimensions and content', () => {
        render(GridItemTestWrapper, { props: defaultProps });

        const gridItem = screen.getByTestId('grid-item');
        expect(gridItem).toHaveStyle({ width: '300px', height: '300px' });
        expect(screen.getByText('Sample content')).toBeInTheDocument();
    });

    it('renders with custom dimensions', () => {
        render(GridItemTestWrapper, {
            props: {
                ...defaultProps,
                width: '50%',
                height: 180
            }
        });

        const gridItem = screen.getByTestId('grid-item');
        expect(gridItem).toHaveStyle({ width: '50%', height: '180px' });
    });

    it('calls onSelect on click and keyboard actions', async () => {
        const onSelect = vi.fn();
        render(GridItemTestWrapper, {
            props: {
                ...defaultProps,
                onSelect
            }
        });

        const gridItem = screen.getByTestId('grid-item');

        await fireEvent.click(gridItem, { shiftKey: true });
        await fireEvent.keyDown(gridItem, { key: 'Enter' });
        await fireEvent.keyDown(gridItem, { key: ' ' });
        await fireEvent.keyDown(gridItem, { key: 'Tab' });

        expect(onSelect).toHaveBeenCalledTimes(3);
        expect(onSelect.mock.calls[0][0].shiftKey).toBe(true);
    });

    it('calls ondblclick on double click', async () => {
        const ondblclick = vi.fn();
        render(GridItemTestWrapper, {
            props: {
                ...defaultProps,
                ondblclick
            }
        });

        const gridItem = screen.getByTestId('grid-item');
        await fireEvent.dblClick(gridItem);

        expect(ondblclick).toHaveBeenCalledTimes(1);
    });

    it('drops draggable grid items on the search target after threshold movement', async () => {
        const onSelect = vi.fn();
        const onGridImageSearchDrop = vi.fn();
        window.addEventListener('lightly:grid-image-search-drop', onGridImageSearchDrop);
        render(GridItemTestWrapper, {
            props: {
                ...defaultProps,
                dragData: {
                    url: '/api/images/sample/sample-1',
                    fileName: 'sample-1.jpg'
                },
                onSelect
            }
        });

        const gridItem = screen.getByTestId('grid-item');
        const searchTarget = document.createElement('div');
        searchTarget.setAttribute('data-grid-search-drop-target', '');
        Object.defineProperty(document, 'elementFromPoint', {
            configurable: true,
            value: vi.fn(() => searchTarget)
        });

        await fireEvent(gridItem, createPointerEvent('pointerdown', { clientX: 10, clientY: 10 }));
        await fireEvent(gridItem, createPointerEvent('pointermove', { clientX: 30, clientY: 10 }));
        expect(screen.getByTestId('grid-item-drag-preview')).toBeInTheDocument();
        expect(gridItem).toHaveAttribute('draggable', 'false');
        expect(gridItem).toHaveClass('cursor-grabbing');
        expect(document.body.style.cursor).toBe('grabbing');

        await fireEvent(gridItem, createPointerEvent('pointerup', { clientX: 30, clientY: 10 }));
        await fireEvent.click(gridItem);

        expect(screen.queryByTestId('grid-item-drag-preview')).not.toBeInTheDocument();
        expect(document.body.style.cursor).toBe('');
        expect(onGridImageSearchDrop).toHaveBeenCalledOnce();
        expect(onGridImageSearchDrop.mock.calls[0][0].detail).toEqual({
            url: '/api/images/sample/sample-1',
            fileName: 'sample-1.jpg'
        });
        expect(onSelect).not.toHaveBeenCalled();

        window.removeEventListener('lightly:grid-image-search-drop', onGridImageSearchDrop);
        vi.restoreAllMocks();
    });

    it('cancels native drag of a thumbnail image so the click reaches onSelect', async () => {
        const onSelect = vi.fn();
        render(GridItemTestWrapper, { props: { ...defaultProps, onSelect } });

        const gridItem = screen.getByTestId('grid-item');
        const thumbnail = document.createElement('img');
        gridItem.appendChild(thumbnail);

        // Browsers fire dragstart on an <img> between mousedown and mouseup as soon as the
        // pointer drifts a few pixels. Unless it is cancelled, the click never fires.
        const dragStart = new Event('dragstart', { bubbles: true, cancelable: true });
        thumbnail.dispatchEvent(dragStart);
        await fireEvent.click(thumbnail);

        expect(dragStart.defaultPrevented).toBe(true);
        expect(onSelect).toHaveBeenCalledTimes(1);
    });

    it('selects once per click when the pointer drifts below the drag threshold', async () => {
        const onSelect = vi.fn();
        render(GridItemTestWrapper, {
            props: {
                ...defaultProps,
                dragData: { url: '/api/images/sample/sample-1', fileName: 'sample-1.jpg' },
                onSelect
            }
        });

        const gridItem = screen.getByTestId('grid-item');
        for (const drift of [3, 5]) {
            await fireEvent(
                gridItem,
                createPointerEvent('pointerdown', { clientX: 10, clientY: 10 })
            );
            await fireEvent(
                gridItem,
                createPointerEvent('pointermove', { clientX: 10 + drift, clientY: 12 })
            );
            await fireEvent(
                gridItem,
                createPointerEvent('pointerup', { clientX: 10 + drift, clientY: 12 })
            );
            await fireEvent.click(gridItem);
        }

        expect(screen.queryByTestId('grid-item-drag-preview')).not.toBeInTheDocument();
        expect(onSelect).toHaveBeenCalledTimes(2);
    });

    it('applies selected style and renders selectable tag', () => {
        render(GridItemTestWrapper, {
            props: {
                ...defaultProps,
                isSelected: true
            }
        });

        const gridItem = screen.getByTestId('grid-item');
        expect(gridItem).toHaveClass('grid-item-selected');
        expect(screen.getByTestId('grid-item-tag')).toBeInTheDocument();
        expect(screen.getByTestId('sample-selected-box')).toBeInTheDocument();
    });

    it('hides selectable tag when tag is false', () => {
        render(GridItemTestWrapper, {
            props: {
                ...defaultProps,
                isSelected: true,
                tag: false
            }
        });

        expect(screen.queryByTestId('sample-selected-box')).not.toBeInTheDocument();
    });

    it('renders caption overlay text', () => {
        render(GridItemTestWrapper, {
            props: {
                ...defaultProps,
                caption: 'caption text'
            }
        });

        expect(screen.getByTestId('grid-item-caption')).toBeInTheDocument();
        const caption = screen.getByText('caption text');
        expect(caption).toBeInTheDocument();
        expect(screen.getByTestId('grid-item-caption-text')).toHaveTextContent('caption text');
        expect(caption).toHaveAttribute('title', 'caption text');
    });

    it('renders qa metadata attributes when provided', () => {
        render(GridItemTestWrapper, {
            props: {
                ...defaultProps,
                dataSampleName: 'sample-001.jpg',
                dataIndex: 7
            }
        });

        const gridItem = screen.getByTestId('grid-item');
        expect(gridItem).toHaveAttribute('data-sample-name', 'sample-001.jpg');
        expect(gridItem).toHaveAttribute('data-index', '7');
    });
});
