import { fireEvent, render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import StrategyCard from './StrategyCard.svelte';
import type { StrategyInstance } from '$lib/hooks/useStrategyBuilder';

const defaultProps = {
    tags: [],
    annotationLabels: [],
    onRemove: vi.fn(),
    onDuplicate: vi.fn(),
    onUpdate: vi.fn(),
    onToggleExpand: vi.fn()
};

describe('StrategyCard', () => {
    beforeEach(() => {
        Element.prototype.scrollIntoView = vi.fn();
    });

    describe('header', () => {
        it('renders the strategy label', () => {
            const instance: StrategyInstance = {
                id: 'abc',
                type: 'diversity',
                params: { strength: 1 },
                isExpanded: true
            };

            render(StrategyCard, { props: { ...defaultProps, instance } });

            expect(screen.getByText('Diversity')).toBeInTheDocument();
        });

        it('calls onToggleExpand when the toggle button is clicked', async () => {
            const onToggleExpand = vi.fn();
            const instance: StrategyInstance = {
                id: 'abc',
                type: 'diversity',
                params: { strength: 1 },
                isExpanded: true
            };

            render(StrategyCard, { props: { ...defaultProps, onToggleExpand, instance } });

            await fireEvent.click(screen.getByTestId('strategy-card-toggle-abc'));

            expect(onToggleExpand).toHaveBeenCalledOnce();
        });

        it('calls onDuplicate when the duplicate button is clicked', async () => {
            const onDuplicate = vi.fn();
            const instance: StrategyInstance = {
                id: 'abc',
                type: 'diversity',
                params: { strength: 1 },
                isExpanded: true
            };

            render(StrategyCard, { props: { ...defaultProps, onDuplicate, instance } });

            await fireEvent.click(screen.getByTestId('strategy-card-duplicate-abc'));

            expect(onDuplicate).toHaveBeenCalledOnce();
        });

        it('disables the duplicate button when isDuplicateDisabled is true', () => {
            const instance: StrategyInstance = {
                id: 'abc',
                type: 'diversity',
                params: { strength: 1 },
                isExpanded: true
            };

            render(StrategyCard, {
                props: { ...defaultProps, instance, isDuplicateDisabled: true }
            });

            expect(screen.getByTestId('strategy-card-duplicate-abc')).toBeDisabled();
        });

        it('calls onRemove when the remove button is clicked', async () => {
            const onRemove = vi.fn();
            const instance: StrategyInstance = {
                id: 'abc',
                type: 'diversity',
                params: { strength: 1 },
                isExpanded: true
            };

            render(StrategyCard, { props: { ...defaultProps, onRemove, instance } });

            await fireEvent.click(screen.getByTestId('strategy-card-remove-abc'));

            expect(onRemove).toHaveBeenCalledOnce();
        });
    });

    describe('collapsed state', () => {
        it('does not render the form when isExpanded is false', () => {
            const instance: StrategyInstance = {
                id: 'abc',
                type: 'diversity',
                params: { strength: 1 },
                isExpanded: false
            };

            render(StrategyCard, { props: { ...defaultProps, instance } });

            expect(
                screen.queryByTestId('strategy-diversity-strength-input-abc')
            ).not.toBeInTheDocument();
        });
    });

    describe('diversity', () => {
        it('renders the strength field when expanded', () => {
            const instance: StrategyInstance = {
                id: 'abc',
                type: 'diversity',
                params: { strength: 1 },
                isExpanded: true
            };

            render(StrategyCard, { props: { ...defaultProps, instance } });

            expect(screen.getByTestId('strategy-diversity-strength-input-abc')).toBeInTheDocument();
        });
    });

    describe('deduplication', () => {
        it('renders the minimum distance and strength fields when expanded', () => {
            const instance: StrategyInstance = {
                id: 'abc',
                type: 'deduplication',
                params: { strength: 1, stopping_condition_minimum_distance: 0.1 },
                isExpanded: true
            };

            render(StrategyCard, { props: { ...defaultProps, instance } });

            expect(
                screen.getByTestId('strategy-deduplication-min-distance-input')
            ).toBeInTheDocument();
            expect(screen.getByTestId('strategy-deduplication-strength-input')).toBeInTheDocument();
        });

        it('calls onUpdate with a new minimum distance', async () => {
            const onUpdate = vi.fn();
            const instance: StrategyInstance = {
                id: 'abc',
                type: 'deduplication',
                params: { strength: 1, stopping_condition_minimum_distance: 0.1 },
                isExpanded: true
            };

            render(StrategyCard, { props: { ...defaultProps, onUpdate, instance } });

            await fireEvent.input(screen.getByTestId('strategy-deduplication-min-distance-input'), {
                target: { value: '0.5' }
            });

            expect(onUpdate).toHaveBeenCalledWith({ stopping_condition_minimum_distance: 0.5 });
        });
    });

    describe('typicality', () => {
        it('renders the strength field when expanded', () => {
            const instance: StrategyInstance = {
                id: 'abc',
                type: 'typicality',
                params: { strength: 1 },
                isExpanded: true
            };

            render(StrategyCard, { props: { ...defaultProps, instance } });

            expect(
                screen.getByTestId('strategy-typicality-strength-input-abc')
            ).toBeInTheDocument();
        });
    });

    describe('similarity', () => {
        it('renders the similarity form when expanded', () => {
            const instance: StrategyInstance = {
                id: 'abc',
                type: 'similarity',
                params: { query_tag_id: '', strength: 1 },
                isExpanded: true
            };

            render(StrategyCard, {
                props: {
                    ...defaultProps,
                    instance,
                    tags: [{ tag_id: 'tag-1', name: 'Tag One' }]
                }
            });

            expect(screen.getByText('Similarity')).toBeInTheDocument();
        });
    });

    describe('metadata_weighting', () => {
        it('renders the metadata weighting form when expanded', () => {
            const instance: StrategyInstance = {
                id: 'abc',
                type: 'metadata_weighting',
                params: { metadata_key: '', strength: 1 },
                isExpanded: true
            };

            render(StrategyCard, { props: { ...defaultProps, instance } });

            expect(screen.getByText('Metadata Weighting')).toBeInTheDocument();
        });

        it('forwards metadataFieldNames to the metadata weighting form', () => {
            const instance: StrategyInstance = {
                id: 'abc',
                type: 'metadata_weighting',
                params: { metadata_key: '', strength: 1 },
                isExpanded: true
            };

            render(StrategyCard, {
                props: {
                    ...defaultProps,
                    instance,
                    metadataFieldNames: ['sharpness', 'brightness']
                }
            });

            expect(screen.getByTestId('strategy-metadata-key-input')).toBeInTheDocument();
        });
    });

    describe('class_balancing', () => {
        it('renders the class balancing form when expanded', () => {
            const instance: StrategyInstance = {
                id: 'abc',
                type: 'class_balancing',
                params: {
                    annotation_source_id: '',
                    target_distribution_mode: 'uniform',
                    target_distribution: [],
                    strength: 1
                },
                isExpanded: true
            };

            render(StrategyCard, {
                props: { ...defaultProps, instance, annotationLabels: ['cat', 'dog'] }
            });

            expect(screen.getByText('Class Balancing')).toBeInTheDocument();
        });

        it('forwards annotationSourceOptions to the class balancing form', async () => {
            const instance: StrategyInstance = {
                id: 'abc',
                type: 'class_balancing',
                params: {
                    annotation_source_id: '',
                    target_distribution_mode: 'uniform',
                    target_distribution: [],
                    strength: 1
                },
                isExpanded: true
            };

            render(StrategyCard, {
                props: {
                    ...defaultProps,
                    instance,
                    annotationLabels: [],
                    annotationSourceOptions: [
                        { id: 'col-1', name: 'ground_truth' },
                        { id: 'col-2', name: 'predictions' }
                    ]
                }
            });

            await fireEvent.keyDown(screen.getByTestId('annotation-source-trigger'), {
                key: 'Enter'
            });

            expect(
                await screen.findByTestId('annotation-source-option-ground_truth')
            ).toBeInTheDocument();
            expect(screen.getByTestId('annotation-source-option-predictions')).toBeInTheDocument();
        });
    });
});
