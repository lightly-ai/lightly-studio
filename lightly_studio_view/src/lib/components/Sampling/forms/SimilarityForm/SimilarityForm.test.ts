import { fireEvent, render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import SimilarityForm from './SimilarityForm.svelte';

describe('SimilarityForm', () => {
    beforeEach(() => {
        Element.prototype.scrollIntoView = vi.fn();
    });

    it('shows "No sample tags available." when tags are empty', async () => {
        render(SimilarityForm, {
            props: {
                params: { query_tag_id: '', strength: 1 },
                tags: [],
                onUpdate: vi.fn()
            }
        });

        await fireEvent.keyDown(screen.getByTestId('similarity-query-tag-select'), {
            key: 'Enter'
        });

        expect(await screen.findByTestId('similarity-no-query-tags')).toBeInTheDocument();
    });

    it('shows tag options when tags are provided', async () => {
        render(SimilarityForm, {
            props: {
                params: { query_tag_id: '', strength: 1 },
                tags: [
                    { tag_id: 'tag-1', name: 'Tag One' },
                    { tag_id: 'tag-2', name: 'Tag Two' }
                ],
                onUpdate: vi.fn()
            }
        });

        await fireEvent.keyDown(screen.getByTestId('similarity-query-tag-select'), {
            key: 'Enter'
        });

        expect(await screen.findByTestId('similarity-query-tag-tag-1')).toBeInTheDocument();
        expect(screen.getByTestId('similarity-query-tag-tag-2')).toBeInTheDocument();
    });

    it('shows the selected tag name in the trigger', () => {
        render(SimilarityForm, {
            props: {
                params: { query_tag_id: 'tag-1', strength: 1 },
                tags: [
                    { tag_id: 'tag-1', name: 'Tag One' },
                    { tag_id: 'tag-2', name: 'Tag Two' }
                ],
                onUpdate: vi.fn()
            }
        });

        expect(screen.getByTestId('similarity-query-tag-select')).toHaveTextContent('Tag One');
    });

    it('calls onUpdate with the selected query_tag_id', async () => {
        const onUpdate = vi.fn();

        render(SimilarityForm, {
            props: {
                params: { query_tag_id: '', strength: 1 },
                tags: [
                    { tag_id: 'tag-1', name: 'Tag One' },
                    { tag_id: 'tag-2', name: 'Tag Two' }
                ],
                onUpdate
            }
        });

        await fireEvent.keyDown(screen.getByTestId('similarity-query-tag-select'), {
            key: 'Enter'
        });
        await fireEvent.pointerUp(await screen.findByTestId('similarity-query-tag-tag-2'));

        expect(onUpdate).toHaveBeenCalledWith({ query_tag_id: 'tag-2' });
    });

    it('calls onUpdate with the new strength value', async () => {
        const onUpdate = vi.fn();

        render(SimilarityForm, {
            props: {
                params: { query_tag_id: '', strength: 1 },
                tags: [],
                onUpdate
            }
        });

        await fireEvent.input(screen.getByTestId('strategy-similarity-strength-input'), {
            target: { value: '2.5' }
        });

        expect(onUpdate).toHaveBeenCalledWith({ strength: 2.5 });
    });
});
