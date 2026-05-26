import { fireEvent, render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import SimilarityForm from './SimilarityForm.svelte';

describe('SimilarityForm', () => {
    beforeEach(() => {
        Element.prototype.scrollIntoView = vi.fn();
    });

    it('shows "Select tag" when no queryTagId is set', () => {
        render(SimilarityForm, {
            props: {
                queryTagId: '',
                tags: [{ tag_id: 'tag-1', name: 'My Tag' }],
                onQueryTagChange: vi.fn()
            }
        });

        expect(screen.getByTestId('selection-dialog-query-tag-select')).toHaveTextContent(
            'Select tag'
        );
    });

    it('shows the name of the selected tag', () => {
        render(SimilarityForm, {
            props: {
                queryTagId: 'tag-1',
                tags: [{ tag_id: 'tag-1', name: 'My Tag' }],
                onQueryTagChange: vi.fn()
            }
        });

        expect(screen.getByTestId('selection-dialog-query-tag-select')).toHaveTextContent('My Tag');
    });

    it('shows an empty state when no tags are provided', async () => {
        render(SimilarityForm, {
            props: { queryTagId: '', tags: [], onQueryTagChange: vi.fn() }
        });

        await fireEvent.keyDown(screen.getByTestId('selection-dialog-query-tag-select'), {
            key: 'Enter'
        });

        expect(await screen.findByTestId('selection-dialog-no-query-tags')).toHaveTextContent(
            'No sample tags available.'
        );
    });

    it('calls onQueryTagChange with the selected tag id', async () => {
        const onQueryTagChange = vi.fn();
        render(SimilarityForm, {
            props: {
                queryTagId: '',
                tags: [
                    { tag_id: 'tag-1', name: 'First Tag' },
                    { tag_id: 'tag-2', name: 'Second Tag' }
                ],
                onQueryTagChange
            }
        });

        await fireEvent.keyDown(screen.getByTestId('selection-dialog-query-tag-select'), {
            key: 'Enter'
        });
        await fireEvent.pointerUp(await screen.findByTestId('selection-query-tag-tag-2'));

        expect(onQueryTagChange).toHaveBeenCalledWith('tag-2');
    });

    it('renders all provided tags in the dropdown', async () => {
        render(SimilarityForm, {
            props: {
                queryTagId: '',
                tags: [
                    { tag_id: 'tag-1', name: 'First Tag' },
                    { tag_id: 'tag-2', name: 'Second Tag' }
                ],
                onQueryTagChange: vi.fn()
            }
        });

        await fireEvent.keyDown(screen.getByTestId('selection-dialog-query-tag-select'), {
            key: 'Enter'
        });

        expect(await screen.findByTestId('selection-query-tag-tag-1')).toBeInTheDocument();
        expect(screen.getByTestId('selection-query-tag-tag-2')).toBeInTheDocument();
    });
});
