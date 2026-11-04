import { fireEvent, render, screen, waitFor, within } from '@testing-library/svelte';
import { QueryClient } from '@tanstack/svelte-query';
import { getColorBySource } from '$lib/utils';
import { setAnnotationClasses, useCustomLabelColors } from '$lib/hooks/useCustomLabelColors';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { AnnotationPairCount } from '$lib/api/lightly_studio_local';
import { writable } from 'svelte/store';
import { useAnnotationTreeState } from '$lib/hooks/useAnnotationTreeState/useAnnotationTreeState';
import AnnotationTreeTestWrapper from './AnnotationTreeTestWrapper.test.svelte';
import type { PairKey } from './pairRows';

const mocks = vi.hoisted(() => ({
    sources: [] as { collection_id: string; name: string }[],
    pairs: [] as AnnotationPairCount[],
    pairsResponse: null as Promise<unknown> | null,
    readImages: vi.fn(),
    colorMode: null as unknown as ReturnType<typeof writable<'class' | 'source'>>,
    setAnnotationColorMode: vi.fn()
}));

vi.mock('$lib/hooks/useSettings', async (importOriginal) => {
    const { writable } = await import('svelte/store');
    const original = await importOriginal<typeof import('$lib/hooks/useSettings')>();
    mocks.colorMode = writable<'class' | 'source'>('class');
    // The real hook saves to the backend, which updates the store the same way.
    mocks.setAnnotationColorMode.mockImplementation(async (mode: 'class' | 'source') => {
        mocks.colorMode.set(mode);
        return { success: true };
    });
    return {
        ...original,
        useSettings: () => ({
            ...original.useSettings(),
            annotationColorModeStore: mocks.colorMode,
            setAnnotationColorMode: mocks.setAnnotationColorMode
        })
    };
});

vi.mock('$lib/api/lightly_studio_local/sdk.gen', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/api/lightly_studio_local/sdk.gen')>()),
    readAnnotationCollections: vi.fn(async () => ({ data: mocks.sources })),
    countImageAnnotationsByPair: vi.fn(() => mocks.pairsResponse ?? { data: mocks.pairs }),
    countUnannotatedImagesBySource: vi.fn(async () => ({
        data: mocks.sources.map((source) => ({
            annotation_collection_id: source.collection_id,
            current_count: 3,
            total_count: 3
        }))
    })),
    readImages: mocks.readImages
}));

const pair = (sourceId: string, labelId: string, name: string): AnnotationPairCount => ({
    annotation_collection_id: sourceId,
    annotation_label_id: labelId,
    label_name: name,
    current_count: 5,
    total_count: 5
});

let testCount = 0;

const renderTree = ({ untickedPairs = [] as PairKey[] } = {}) => {
    testCount += 1;
    const collectionId = `images-${testCount}`;
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    // The tree state lives in session storage per collection, so each test gets its own.
    useAnnotationTreeState(collectionId).setTicked(untickedPairs, false);
    render(AnnotationTreeTestWrapper, { client, collectionId });
};

const UNTICKED_CAR = [{ collection_id: 'src-labels', annotation_label_id: 'lbl-car' }];

const groupNamed = async (name: string) => {
    const groups = await screen.findAllByTestId('annotation-tree-group');
    const group = groups.find(
        (element) => within(element).getByTestId('annotation-tree-group-name').textContent === name
    );
    if (!group) throw new Error(`No group named ${name}`);
    return group;
};

const childNames = (group: HTMLElement) =>
    within(group)
        .queryAllByTestId('annotation-tree-row-name')
        .map((element) => element.textContent);

describe('AnnotationTree', () => {
    beforeEach(() => {
        mocks.sources = [
            { collection_id: 'src-labels', name: 'labels' },
            { collection_id: 'src-model', name: 'model_v1' }
        ];
        mocks.pairs = [
            pair('src-labels', 'lbl-car', 'car'),
            pair('src-labels', 'lbl-person', 'person'),
            pair('src-model', 'lbl-car', 'car')
        ];
        mocks.pairsResponse = null;
        mocks.colorMode?.set('class');
        mocks.setAnnotationColorMode.mockClear();
        mocks.readImages.mockReset();
        mocks.readImages.mockResolvedValue({
            data: { data: [], total_count: 0, nextCursor: null }
        });
    });

    it('renders a source with "No annotations" first and its classes indented under it', async () => {
        renderTree();

        const labels = await groupNamed('labels');
        await waitFor(() =>
            expect(childNames(labels)).toEqual(['No annotations', 'car', 'person'])
        );
        expect(within(labels).getByTestId('annotation-tree-children')).toBeInTheDocument();
    });

    it('sends every pair except the unticked one with the images query', async () => {
        renderTree();

        await fireEvent.click(await screen.findByRole('checkbox', { name: 'car in labels' }));

        await waitFor(() =>
            expect(mocks.readImages).toHaveBeenLastCalledWith(
                expect.objectContaining({
                    body: expect.objectContaining({
                        filters: expect.objectContaining({
                            sample_filter: expect.objectContaining({
                                annotations_filter: {
                                    filter_type: 'annotations',
                                    annotation_pairs: [
                                        {
                                            collection_id: 'src-labels',
                                            annotation_label_id: 'lbl-person'
                                        },
                                        {
                                            collection_id: 'src-model',
                                            annotation_label_id: 'lbl-car'
                                        }
                                    ],
                                    unannotated_collection_ids: ['src-labels', 'src-model']
                                }
                            })
                        })
                    })
                })
            )
        );
    });

    it('shows a dash on the group checkbox when some children are unticked', async () => {
        renderTree();

        await fireEvent.click(await screen.findByRole('checkbox', { name: 'car in labels' }));

        await waitFor(() =>
            expect(screen.getByRole('checkbox', { name: 'labels' })).toHaveAttribute(
                'aria-checked',
                'mixed'
            )
        );
    });

    it('groups a class across sources "By class"', async () => {
        renderTree();

        await fireEvent.click(await screen.findByRole('button', { name: 'By class' }));

        const car = await groupNamed('car');
        await waitFor(() => expect(childNames(car)).toEqual(['labels', 'model_v1']));
    });

    it('keeps the source "No annotations" ticked on "Only" for a source', async () => {
        renderTree();

        await fireEvent.click(await screen.findByRole('button', { name: 'Only labels' }));

        await waitFor(() =>
            expect(screen.getByRole('checkbox', { name: 'model_v1' })).toHaveAttribute(
                'aria-checked',
                'false'
            )
        );
        expect(screen.getByRole('checkbox', { name: 'labels' })).toHaveAttribute(
            'aria-checked',
            'true'
        );
    });

    it('unticks every "No annotations" row on "Only" for a class', async () => {
        renderTree();

        await fireEvent.click(await screen.findByRole('button', { name: 'Only car in labels' }));

        await waitFor(() =>
            expect(
                screen.getByRole('checkbox', { name: 'No annotations in labels' })
            ).toHaveAttribute('aria-checked', 'false')
        );
        expect(screen.getByRole('checkbox', { name: 'car in labels' })).toHaveAttribute(
            'aria-checked',
            'true'
        );
    });

    it('holds the images request back while the pair counts load with a row unticked', async () => {
        mocks.pairsResponse = new Promise(() => {});
        renderTree({ untickedPairs: UNTICKED_CAR });

        await screen.findAllByTestId('annotation-tree-group');
        expect(mocks.readImages).not.toHaveBeenCalled();
    });

    it('sends the images request at once while the pair counts load with nothing unticked', async () => {
        mocks.pairsResponse = new Promise(() => {});
        renderTree();

        await waitFor(() => expect(mocks.readImages).toHaveBeenCalled());
        const [request] = mocks.readImages.mock.calls[0];
        expect(request.body.filters.sample_filter.annotations_filter).toBeUndefined();
    });

    it('sends the images request without a tree filter when the pair counts fail', async () => {
        mocks.pairsResponse = Promise.reject(new Error('count failed'));
        renderTree({ untickedPairs: UNTICKED_CAR });

        await waitFor(() => expect(mocks.readImages).toHaveBeenCalled());
        const [request] = mocks.readImages.mock.calls[0];
        expect(request.body.filters.sample_filter.annotations_filter).toBeUndefined();
    });

    it('sends the images request without a tree filter when nothing is unticked', async () => {
        renderTree();

        await waitFor(() => expect(mocks.readImages).toHaveBeenCalled());
        const [request] = mocks.readImages.mock.calls[0];
        expect(request.body.filters.sample_filter.annotations_filter).toBeUndefined();
    });

    it('ticks only the class pairs and no "No annotations" row on a class bar click', async () => {
        renderTree();

        await screen.findByRole('checkbox', { name: 'car in labels' });
        await fireEvent.click(screen.getByRole('button', { name: 'Class bar car' }));

        await waitFor(() =>
            expect(screen.getByRole('checkbox', { name: 'person in labels' })).toHaveAttribute(
                'aria-checked',
                'false'
            )
        );
        expect(screen.getByRole('checkbox', { name: 'car in model_v1' })).toHaveAttribute(
            'aria-checked',
            'true'
        );
        expect(
            screen.getByRole('checkbox', { name: 'No annotations in model_v1' })
        ).toHaveAttribute('aria-checked', 'false');
    });

    it('toggles the eye of an unticked row and dims it', async () => {
        renderTree();

        await fireEvent.click(await screen.findByRole('checkbox', { name: 'car in labels' }));
        const eye = screen.getByRole('button', { name: 'Show car in labels' });
        await waitFor(() => expect(eye).toHaveClass('opacity-50'));
        expect(eye).toHaveAttribute('aria-pressed', 'true');

        await fireEvent.click(eye);

        await waitFor(() => expect(eye).toHaveAttribute('aria-pressed', 'false'));
        expect(screen.getByRole('checkbox', { name: 'car in labels' })).toHaveAttribute(
            'aria-checked',
            'false'
        );
    });

    it('hides all children with the group eye and shows a dimmed eye when partly visible', async () => {
        renderTree();

        await fireEvent.click(await screen.findByRole('button', { name: 'Show car in labels' }));
        const groupEye = screen.getByRole('button', { name: 'Show labels' });
        await waitFor(() => expect(groupEye).toHaveAttribute('aria-pressed', 'mixed'));

        await fireEvent.click(groupEye);
        await fireEvent.click(groupEye);

        await waitFor(() => expect(groupEye).toHaveAttribute('aria-pressed', 'false'));
        for (const name of ['car in labels', 'person in labels']) {
            expect(screen.getByRole('button', { name: `Show ${name}` })).toHaveAttribute(
                'aria-pressed',
                'false'
            );
        }
        expect(screen.getByRole('button', { name: 'Show car in model_v1' })).toHaveAttribute(
            'aria-pressed',
            'true'
        );
        expect(screen.queryByRole('button', { name: 'Show No annotations in labels' })).toBeNull();
    });

    it('hides a class in every source with its eye "By class"', async () => {
        renderTree();

        await fireEvent.click(await screen.findByRole('button', { name: 'By class' }));
        await fireEvent.click(await screen.findByRole('button', { name: 'Show car' }));

        await waitFor(() =>
            expect(screen.getByRole('button', { name: 'Show car in labels' })).toHaveAttribute(
                'aria-pressed',
                'false'
            )
        );
        expect(screen.getByRole('button', { name: 'Show car in model_v1' })).toHaveAttribute(
            'aria-pressed',
            'false'
        );
        expect(screen.getByRole('button', { name: 'Show person' })).toHaveAttribute(
            'aria-pressed',
            'true'
        );
    });

    it('starts collapsed with 4 sources', async () => {
        mocks.sources = ['a', 'b', 'c', 'd'].map((name) => ({
            collection_id: `src-${name}`,
            name
        }));
        mocks.pairs = mocks.sources.map((source) => pair(source.collection_id, 'lbl-car', 'car'));
        renderTree();

        await waitFor(() => expect(screen.getAllByTestId('annotation-tree-group')).toHaveLength(4));
        for (const name of ['a', 'b', 'c', 'd']) {
            expect(screen.getByRole('button', { name: `Expand ${name}` })).toHaveAttribute(
                'aria-expanded',
                'false'
            );
        }
        expect(screen.queryAllByTestId('annotation-tree-row-name')).toHaveLength(0);
    });
    describe('search', () => {
        const typeQuery = async (query: string) =>
            fireEvent.input(screen.getByRole('textbox', { name: /^Search/ }), {
                target: { value: query }
            });

        it('shows only matching rows with the match highlighted and opens their groups', async () => {
            mocks.sources = ['a', 'b', 'c', 'd'].map((name) => ({
                collection_id: `src-${name}`,
                name
            }));
            mocks.pairs = [
                pair('src-a', 'lbl-car', 'car'),
                pair('src-a', 'lbl-person', 'person'),
                pair('src-b', 'lbl-person', 'person')
            ];
            renderTree();
            await screen.findAllByTestId('annotation-tree-group');

            await fireEvent.click(screen.getByRole('button', { name: 'Use regular expression' }));
            await typeQuery('^ca');

            await waitFor(() =>
                expect(screen.getAllByTestId('annotation-tree-group')).toHaveLength(1)
            );
            const group = await groupNamed('a');
            expect(childNames(group)).toEqual(['car']);
            expect(within(group).getByText('ca').tagName).toBe('MARK');
        });

        it('turns the field red and shows "Invalid pattern" for a broken regex', async () => {
            renderTree();
            await screen.findAllByTestId('annotation-tree-group');

            await fireEvent.click(screen.getByRole('button', { name: 'Use regular expression' }));
            await typeQuery('(');

            expect(await screen.findByText('Invalid pattern')).toBeInTheDocument();
            expect(screen.getByRole('textbox', { name: /^Search/ })).toHaveAttribute(
                'aria-invalid',
                'true'
            );
        });

        it('restores the stored open state when the search is cleared', async () => {
            mocks.sources = ['a', 'b', 'c', 'd'].map((name) => ({
                collection_id: `src-${name}`,
                name
            }));
            mocks.pairs = mocks.sources.map((source) =>
                pair(source.collection_id, 'lbl-car', 'car')
            );
            renderTree();
            await screen.findAllByTestId('annotation-tree-group');

            await typeQuery('car');
            await waitFor(() =>
                expect(screen.queryAllByTestId('annotation-tree-row-name').length).toBeGreaterThan(
                    0
                )
            );
            await typeQuery('');

            await waitFor(() =>
                expect(screen.queryAllByTestId('annotation-tree-row-name')).toHaveLength(0)
            );
        });

        it('matches source names "By class" and drops the other children', async () => {
            renderTree();
            await fireEvent.click(await screen.findByRole('button', { name: 'By class' }));
            await screen.findByRole('checkbox', { name: 'car in labels' });

            await typeQuery('labels');

            await waitFor(() =>
                expect(screen.getAllByTestId('annotation-tree-group')).toHaveLength(2)
            );
            for (const name of ['car', 'person']) {
                const group = await groupNamed(name);
                expect(childNames(group)).toEqual(['labels']);
                expect(within(group).getByText('labels').tagName).toBe('MARK');
            }

            await fireEvent.click(screen.getByRole('checkbox', { name: 'All annotations' }));

            await waitFor(() =>
                expect(screen.getByRole('checkbox', { name: 'car in labels' })).toHaveAttribute(
                    'aria-checked',
                    'false'
                )
            );
            expect(screen.getByRole('checkbox', { name: 'person in labels' })).toHaveAttribute(
                'aria-checked',
                'false'
            );
            await typeQuery('');
            expect(
                await screen.findByRole('checkbox', { name: 'car in model_v1' })
            ).toHaveAttribute('aria-checked', 'true');
        });

        it('unticks only the matches with "All annotations" while searching', async () => {
            renderTree();
            await screen.findByRole('checkbox', { name: 'car in labels' });

            await typeQuery('car');
            await fireEvent.click(await screen.findByRole('checkbox', { name: 'All annotations' }));

            await waitFor(() =>
                expect(screen.getByRole('checkbox', { name: 'car in labels' })).toHaveAttribute(
                    'aria-checked',
                    'false'
                )
            );
            expect(screen.getByRole('checkbox', { name: 'car in model_v1' })).toHaveAttribute(
                'aria-checked',
                'false'
            );
            await typeQuery('');
            expect(
                await screen.findByRole('checkbox', { name: 'person in labels' })
            ).toHaveAttribute('aria-checked', 'true');
        });
    });

    describe('color marks', () => {
        const sourceIconOf = (group: HTMLElement) =>
            within(group).getAllByTestId('annotation-tree-source-icon')[0];

        it('shows neutral source icons and class dots "By class" in the Class mode', async () => {
            renderTree();

            const labels = await groupNamed('labels');
            expect(sourceIconOf(labels)).not.toHaveAttribute('data-color');
            await waitFor(() =>
                expect(within(labels).getAllByTestId('annotation-tree-class-dot')).toHaveLength(2)
            );
        });

        it('colors the class dots with the class colors saved in the dataset', async () => {
            setAnnotationClasses('ds-1', [
                {
                    annotation_label_id: 'lbl-car',
                    annotation_label_name: 'car',
                    dataset_id: 'ds-1',
                    color: '#123456',
                    alpha: 1
                }
            ]);
            renderTree();

            try {
                const labels = await groupNamed('labels');
                await waitFor(() =>
                    expect(
                        within(labels).getAllByTestId('annotation-tree-class-dot')[0]
                    ).toHaveStyle({ backgroundColor: '#123456' })
                );
            } finally {
                useCustomLabelColors().clearCustomColors();
            }
        });

        it('calls setAnnotationColorMode from the Color by switch', async () => {
            renderTree();

            await fireEvent.click(await screen.findByRole('button', { name: 'Source' }));

            expect(mocks.setAnnotationColorMode).toHaveBeenCalledWith('source');
            await waitFor(() =>
                expect(screen.getByRole('button', { name: 'Source' })).toHaveAttribute(
                    'aria-pressed',
                    'true'
                )
            );
        });

        it('tints the source icon in the source color and drops the class dots in the Source mode', async () => {
            mocks.colorMode?.set('source');
            renderTree();

            const labels = await groupNamed('labels');
            const expected = getColorBySource('labels', 1).color;
            expect(sourceIconOf(labels)).toHaveAttribute('data-color', expected);
            expect(within(labels).queryByTestId('annotation-tree-class-dot')).toBeNull();
        });

        it('opens the color picker from the source color mark in the Source mode', async () => {
            mocks.colorMode?.set('source');
            renderTree();

            await groupNamed('labels');
            await fireEvent.click(
                (await screen.findAllByRole('img', { name: 'Change color of labels' }))[0]
            );

            expect(await screen.findByRole('dialog', { name: 'Color picker' })).toBeInTheDocument();
        });

        it('does not open a picker from the neutral source icon in the Class mode', async () => {
            renderTree();

            const labels = await groupNamed('labels');
            await fireEvent.click(sourceIconOf(labels));

            expect(screen.queryByRole('dialog', { name: 'Color picker' })).toBeNull();
        });
    });
});
