import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import StrategyCard from './StrategyCard.svelte';
import type { StrategyInstance } from '../useStrategyBuilder/useStrategyBuilder';

const tags = [{ tag_id: 'tag-1', name: 'Query Tag' }];

function renderStrategyCard(instance: StrategyInstance) {
    return render(StrategyCard, {
        props: {
            instance,
            tags,
            onRemove: vi.fn(),
            onDuplicate: vi.fn(),
            onUpdate: vi.fn(),
            onToggleExpand: vi.fn()
        }
    });
}

describe('StrategyCard', () => {
    it('shows the strategy label', () => {
        renderStrategyCard({
            id: 'strategy-1',
            type: 'diversity',
            params: { embedding_model_name: '', strength: 1 },
            isExpanded: true
        });

        expect(screen.getByText('Diversity')).toBeInTheDocument();
    });

    it('shows a parameter summary when collapsed', () => {
        renderStrategyCard({
            id: 'strategy-1',
            type: 'metadata_weighting',
            params: { metadata_key: 'weather', strength: 1 },
            isExpanded: false
        });

        expect(screen.getByText('weather')).toBeInTheDocument();
    });

    it('calls onToggleExpand when the header is clicked', async () => {
        const onToggleExpand = vi.fn();

        render(StrategyCard, {
            props: {
                instance: {
                    id: 'strategy-1',
                    type: 'diversity',
                    params: { embedding_model_name: '', strength: 1 },
                    isExpanded: true
                },
                tags,
                onRemove: vi.fn(),
                onDuplicate: vi.fn(),
                onUpdate: vi.fn(),
                onToggleExpand
            }
        });

        await fireEvent.click(screen.getByTestId('strategy-card-toggle-strategy-1'));

        expect(onToggleExpand).toHaveBeenCalledOnce();
    });

    it('calls onRemove when the remove button is clicked', async () => {
        const onRemove = vi.fn();

        render(StrategyCard, {
            props: {
                instance: {
                    id: 'strategy-1',
                    type: 'diversity',
                    params: { embedding_model_name: '', strength: 1 },
                    isExpanded: true
                },
                tags,
                onRemove,
                onDuplicate: vi.fn(),
                onUpdate: vi.fn(),
                onToggleExpand: vi.fn()
            }
        });

        await fireEvent.click(screen.getByTestId('strategy-card-remove-strategy-1'));

        expect(onRemove).toHaveBeenCalledOnce();
    });

    it('calls onDuplicate when the duplicate button is clicked', async () => {
        const onDuplicate = vi.fn();

        render(StrategyCard, {
            props: {
                instance: {
                    id: 'strategy-1',
                    type: 'diversity',
                    params: { embedding_model_name: '', strength: 1 },
                    isExpanded: true
                },
                tags,
                onRemove: vi.fn(),
                onDuplicate,
                onUpdate: vi.fn(),
                onToggleExpand: vi.fn()
            }
        });

        await fireEvent.click(screen.getByTestId('strategy-card-duplicate-strategy-1'));

        expect(onDuplicate).toHaveBeenCalledOnce();
    });

    it('renders the correct form for each strategy type', () => {
        const strategies: StrategyInstance[] = [
            {
                id: 'diversity',
                type: 'diversity',
                params: { embedding_model_name: '', strength: 1 },
                isExpanded: true
            },
            {
                id: 'typicality',
                type: 'typicality',
                params: { strength: 1 },
                isExpanded: true
            },
            {
                id: 'similarity',
                type: 'similarity',
                params: { query_tag_id: '', embedding_model_name: '', strength: 1 },
                isExpanded: true
            },
            {
                id: 'metadata',
                type: 'metadata_weighting',
                params: { metadata_key: '', strength: 1 },
                isExpanded: true
            },
            {
                id: 'balancing',
                type: 'class_balancing',
                params: { target_distribution: [], strength: 1 },
                isExpanded: true
            }
        ];

        const expectedFormTestIds = [
            'diversity-form',
            'typicality-form',
            'similarity-form',
            'metadata-weighting-form',
            'class-balancing-form'
        ];

        strategies.forEach((instance, index) => {
            const { unmount } = renderStrategyCard(instance);
            expect(screen.getByTestId(expectedFormTestIds[index])).toBeInTheDocument();
            unmount();
        });
    });
});
