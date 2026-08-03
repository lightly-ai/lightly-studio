import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import GridContextMenuTagList from './GridContextMenuTagList.svelte';

const defaultProps = {
    tags: [
        { tag_id: 'tag-train', name: 'train' },
        { tag_id: 'tag-blurry', name: 'blurry' }
    ],
    tagStates: { 'tag-train': 'checked', 'tag-blurry': 'unchecked' } as Record<
        string,
        'checked' | 'indeterminate' | 'unchecked'
    >,
    busy: false,
    onToggle: vi.fn(),
    onCreate: vi.fn()
};

describe('GridContextMenuTagList', () => {
    it('exposes each tag with its checked state', () => {
        render(GridContextMenuTagList, {
            props: {
                ...defaultProps,
                tagStates: { 'tag-train': 'checked', 'tag-blurry': 'indeterminate' }
            }
        });

        expect(screen.getByTestId('context-menu-tag-train')).toHaveAttribute(
            'aria-checked',
            'true'
        );
        expect(screen.getByTestId('context-menu-tag-blurry')).toHaveAttribute(
            'aria-checked',
            'mixed'
        );
    });

    it('toggles the clicked tag', async () => {
        const onToggle = vi.fn();
        render(GridContextMenuTagList, { props: { ...defaultProps, onToggle } });

        await fireEvent.click(screen.getByTestId('context-menu-tag-train'));

        expect(onToggle).toHaveBeenCalledWith('tag-train');
    });

    it('narrows the list to the search query', async () => {
        render(GridContextMenuTagList, { props: defaultProps });

        await fireEvent.input(screen.getByPlaceholderText('Search tags…'), {
            target: { value: 'blur' }
        });

        expect(screen.getByTestId('context-menu-tag-blurry')).toBeInTheDocument();
        expect(screen.queryByTestId('context-menu-tag-train')).not.toBeInTheDocument();
    });

    it('creates a tag using the trimmed query', async () => {
        const onCreate = vi.fn();
        render(GridContextMenuTagList, { props: { ...defaultProps, onCreate } });

        await fireEvent.input(screen.getByPlaceholderText('Search tags…'), {
            target: { value: '  night  ' }
        });
        await fireEvent.click(screen.getByTestId('context-menu-create-tag'));

        expect(onCreate).toHaveBeenCalledWith('night');
    });

    it('does not offer create for an existing tag in a different case', async () => {
        render(GridContextMenuTagList, { props: defaultProps });

        await fireEvent.input(screen.getByPlaceholderText('Search tags…'), {
            target: { value: 'TRAIN' }
        });

        expect(screen.queryByTestId('context-menu-create-tag')).not.toBeInTheDocument();
    });

    it('ignores interaction while a mutation is in flight', async () => {
        const onToggle = vi.fn();
        render(GridContextMenuTagList, { props: { ...defaultProps, busy: true, onToggle } });

        await fireEvent.click(screen.getByTestId('context-menu-tag-train'));

        expect(onToggle).not.toHaveBeenCalled();
        expect(screen.getByPlaceholderText('Search tags…')).toBeDisabled();
    });

    it('shows the loaded-targets note when one is given', () => {
        render(GridContextMenuTagList, {
            props: { ...defaultProps, knownTargetNote: 'State shown for 2 of 40 loaded samples' }
        });

        expect(screen.getByText('State shown for 2 of 40 loaded samples')).toBeInTheDocument();
    });
});
