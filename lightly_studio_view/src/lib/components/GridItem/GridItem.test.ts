import { describe, it, expect, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import GridItemTestWrapper from './GridItemTestWrapper.test.svelte';

describe('GridItem', () => {
    const defaultProps = {
        content: 'Sample content'
    };

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
