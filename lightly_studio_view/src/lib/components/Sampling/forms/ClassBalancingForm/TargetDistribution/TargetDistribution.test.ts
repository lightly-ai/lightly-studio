import { fireEvent, render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import TargetDistribution from './TargetDistribution.svelte';

describe('TargetDistribution', () => {
    beforeEach(() => {
        Element.prototype.scrollIntoView = vi.fn();
    });

    it('shows an empty state when there are no rows', () => {
        render(TargetDistribution, {
            props: {
                targetDistribution: [],
                annotationLabels: [],
                onUpdate: vi.fn()
            }
        });

        expect(screen.getByTestId('class-balancing-empty-state')).toBeInTheDocument();
    });

    it('hides the empty state when rows are present', () => {
        render(TargetDistribution, {
            props: {
                targetDistribution: [{ class_name: 'cat', weight: 0.5 }],
                annotationLabels: ['cat'],
                onUpdate: vi.fn()
            }
        });

        expect(screen.queryByTestId('class-balancing-empty-state')).not.toBeInTheDocument();
    });

    it('calls onUpdate with a new row when "Add class" is clicked', async () => {
        const onUpdate = vi.fn();

        render(TargetDistribution, {
            props: {
                targetDistribution: [],
                annotationLabels: [],
                onUpdate
            }
        });

        await fireEvent.click(screen.getByTestId('class-balancing-add-row'));

        expect(onUpdate).toHaveBeenCalledWith([{ class_name: '', weight: 0 }]);
    });

    it('renders existing rows', () => {
        render(TargetDistribution, {
            props: {
                targetDistribution: [
                    { class_name: 'cat', weight: 0.2 },
                    { class_name: 'dog', weight: 0.8 }
                ],
                annotationLabels: ['cat', 'dog'],
                onUpdate: vi.fn()
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
                targetDistribution: [{ class_name: 'cat', weight: 0.2 }],
                annotationLabels: ['cat'],
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
                targetDistribution: [
                    { class_name: 'cat', weight: 0.2 },
                    { class_name: 'dog', weight: 0.8 }
                ],
                annotationLabels: ['cat', 'dog'],
                onUpdate
            }
        });

        await fireEvent.click(screen.getByTestId('class-balancing-remove-row-0'));

        expect(onUpdate).toHaveBeenCalledWith([{ class_name: 'dog', weight: 0.8 }]);
    });

    it('calls onUpdate with the selected class name', async () => {
        const onUpdate = vi.fn();

        render(TargetDistribution, {
            props: {
                targetDistribution: [{ class_name: '', weight: 0 }],
                annotationLabels: ['cat', 'dog'],
                onUpdate
            }
        });

        await fireEvent.keyDown(screen.getByTestId('class-balancing-class-name-0'), {
            key: 'Enter'
        });
        await fireEvent.pointerUp(await screen.findByTestId('class-balancing-class-name-0-cat'));

        expect(onUpdate).toHaveBeenCalledWith([{ class_name: 'cat', weight: 0 }]);
    });
});
