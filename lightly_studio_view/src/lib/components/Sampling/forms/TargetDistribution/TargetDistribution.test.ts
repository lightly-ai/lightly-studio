import { fireEvent, render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import TargetDistribution from './TargetDistribution.svelte';

const defaultProps = {
    targetDistribution: [],
    options: [],
    onUpdate: vi.fn()
};

describe('TargetDistribution', () => {
    beforeEach(() => {
        Element.prototype.scrollIntoView = vi.fn();
    });

    it('shows an empty state when there are no rows', () => {
        render(TargetDistribution, { props: { ...defaultProps } });

        expect(screen.getByTestId('class-balancing-empty-state')).toBeInTheDocument();
    });

    it('hides the empty state when rows are present', () => {
        render(TargetDistribution, {
            props: {
                ...defaultProps,
                targetDistribution: [{ class_name: 'cat', weight: 0.5 }],
                options: ['cat']
            }
        });

        expect(screen.queryByTestId('class-balancing-empty-state')).not.toBeInTheDocument();
    });

    it('calls onUpdate with a new row when the add button is clicked', async () => {
        const onUpdate = vi.fn();

        render(TargetDistribution, { props: { ...defaultProps, onUpdate } });

        await fireEvent.click(screen.getByTestId('class-balancing-add-row'));

        expect(onUpdate).toHaveBeenCalledWith([{ class_name: '', weight: 0 }]);
    });

    it('renders existing rows', () => {
        render(TargetDistribution, {
            props: {
                ...defaultProps,
                targetDistribution: [
                    { class_name: 'cat', weight: 0.2 },
                    { class_name: 'dog', weight: 0.8 }
                ],
                options: ['cat', 'dog']
            }
        });

        expect(screen.getByTestId('class-balancing-class-name-0')).toBeInTheDocument();
        expect(screen.getByTestId('class-balancing-weight-0')).toHaveValue(0.2);
        expect(screen.getByTestId('class-balancing-class-name-1')).toBeInTheDocument();
        expect(screen.getByTestId('class-balancing-weight-1')).toHaveValue(0.8);
    });

    it('calls onUpdate with updated weight when a weight input changes', async () => {
        const onUpdate = vi.fn();

        render(TargetDistribution, {
            props: {
                ...defaultProps,
                targetDistribution: [{ class_name: 'cat', weight: 0.2 }],
                options: ['cat'],
                onUpdate
            }
        });

        await fireEvent.input(screen.getByTestId('class-balancing-weight-0'), {
            target: { value: '0.5' }
        });

        expect(onUpdate).toHaveBeenCalledWith([{ class_name: 'cat', weight: 0.5 }]);
    });

    it('calls onUpdate without the removed row when the remove button is clicked', async () => {
        const onUpdate = vi.fn();

        render(TargetDistribution, {
            props: {
                ...defaultProps,
                targetDistribution: [
                    { class_name: 'cat', weight: 0.2 },
                    { class_name: 'dog', weight: 0.8 }
                ],
                options: ['cat', 'dog'],
                onUpdate
            }
        });

        await fireEvent.click(screen.getByTestId('class-balancing-remove-row-0'));

        expect(onUpdate).toHaveBeenCalledWith([{ class_name: 'dog', weight: 0.8 }]);
    });

    it('calls onUpdate with the selected option', async () => {
        const onUpdate = vi.fn();

        render(TargetDistribution, {
            props: {
                ...defaultProps,
                targetDistribution: [{ class_name: '', weight: 0 }],
                options: ['cat', 'dog'],
                onUpdate
            }
        });

        await fireEvent.keyDown(screen.getByTestId('class-balancing-class-name-0'), {
            key: 'Enter'
        });
        await fireEvent.pointerUp(await screen.findByTestId('class-balancing-class-name-0-cat'));

        expect(onUpdate).toHaveBeenCalledWith([{ class_name: 'cat', weight: 0 }]);
    });

    it('does not offer an option already taken by another row', async () => {
        render(TargetDistribution, {
            props: {
                ...defaultProps,
                targetDistribution: [
                    { class_name: 'cat', weight: 0.2 },
                    { class_name: '', weight: 0 }
                ],
                options: ['cat', 'dog']
            }
        });

        await fireEvent.keyDown(screen.getByTestId('class-balancing-class-name-1'), {
            key: 'Enter'
        });

        expect(await screen.findByTestId('class-balancing-class-name-1-dog')).toBeInTheDocument();
        expect(screen.queryByTestId('class-balancing-class-name-1-cat')).not.toBeInTheDocument();
    });

    it('keeps its own value selectable in the row that holds it', async () => {
        render(TargetDistribution, {
            props: {
                ...defaultProps,
                targetDistribution: [{ class_name: 'cat', weight: 0.2 }],
                options: ['cat', 'dog']
            }
        });

        await fireEvent.keyDown(screen.getByTestId('class-balancing-class-name-0'), {
            key: 'Enter'
        });

        expect(await screen.findByTestId('class-balancing-class-name-0-cat')).toBeInTheDocument();
    });

    it('renders the annotation class wording by default', () => {
        render(TargetDistribution, { props: { ...defaultProps } });

        expect(screen.getByTestId('class-balancing-add-row')).toHaveTextContent(
            'Add annotation class'
        );
        expect(screen.getByTestId('class-balancing-empty-state')).toHaveTextContent(
            'Add at least one annotation class to balance against.'
        );
    });

    it('renders the given item label instead of the annotation class wording', () => {
        render(TargetDistribution, {
            props: {
                ...defaultProps,
                targetDistribution: [{ class_name: 'sunny', weight: 0.3 }],
                options: ['sunny'],
                itemLabel: 'metadata value'
            }
        });

        expect(screen.getByTestId('class-balancing-add-row')).toHaveTextContent(
            'Add metadata value'
        );
        expect(screen.getByRole('button', { name: 'Remove metadata value 1' })).toBeInTheDocument();
    });
});
