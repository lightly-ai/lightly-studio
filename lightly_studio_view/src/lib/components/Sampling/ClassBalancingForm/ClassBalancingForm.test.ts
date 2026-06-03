import { fireEvent, render, screen } from '@testing-library/svelte';
import type { ComponentProps } from 'svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ClassBalancingForm from './ClassBalancingForm.svelte';

type MockAnnotationLabel = {
    dataset_id: string;
    annotation_label_name: string;
    annotation_label_id: string;
};

const mockData = vi.hoisted(() => ({
    annotationLabels: [] as MockAnnotationLabel[]
}));

vi.mock('$lib/hooks/useAnnotationLabels/useAnnotationLabels', () => ({
    useAnnotationLabels: () => ({ data: mockData.annotationLabels })
}));

type ClassBalancingFormProps = ComponentProps<typeof ClassBalancingForm>;

function renderClassBalancingForm(props: Partial<ClassBalancingFormProps> = {}) {
    return render(ClassBalancingForm, {
        props: {
            collectionId: 'collection-1',
            balancingMode: 'uniform',
            classTargets: {},
            annotationCollections: [],
            annotationSourceId: '',
            onBalancingModeChange: vi.fn(),
            onClassTargetsChange: vi.fn(),
            onAnnotationSourceChange: vi.fn(),
            ...props
        }
    });
}

describe('ClassBalancingForm', () => {
    beforeEach(() => {
        mockData.annotationLabels = [
            {
                dataset_id: 'dataset-1',
                annotation_label_name: 'cat',
                annotation_label_id: 'label-1'
            },
            {
                dataset_id: 'dataset-1',
                annotation_label_name: 'dog',
                annotation_label_id: 'label-2'
            }
        ];
        Element.prototype.scrollIntoView = vi.fn();
    });

    it('shows the current balancing mode label', () => {
        renderClassBalancingForm();

        expect(screen.getByTestId('sampling-dialog-balancing-mode-select')).toHaveTextContent(
            'Uniform'
        );
    });

    it('shows the uniform option in the dropdown', async () => {
        renderClassBalancingForm();

        await fireEvent.keyDown(screen.getByTestId('sampling-dialog-balancing-mode-select'), {
            key: 'Enter'
        });

        expect(await screen.findByTestId('sampling-balancing-mode-uniform')).toBeInTheDocument();
    });

    it('shows input balancing mode as enabled', async () => {
        renderClassBalancingForm();

        await fireEvent.keyDown(screen.getByTestId('sampling-dialog-balancing-mode-select'), {
            key: 'Enter'
        });

        const inputOption = await screen.findByTestId('sampling-balancing-mode-input');
        expect(inputOption).not.toHaveAttribute('data-disabled');
        expect(inputOption).toHaveTextContent('Input');
    });

    it('calls onBalancingModeChange when input mode is selected', async () => {
        const onBalancingModeChange = vi.fn();
        renderClassBalancingForm({ onBalancingModeChange });

        await fireEvent.keyDown(screen.getByTestId('sampling-dialog-balancing-mode-select'), {
            key: 'Enter'
        });

        const inputOption = await screen.findByTestId('sampling-balancing-mode-input');
        await fireEvent.pointerUp(inputOption);

        expect(onBalancingModeChange).toHaveBeenCalledWith('input');
    });

    it('shows dictionary balancing mode as enabled', async () => {
        renderClassBalancingForm();

        await fireEvent.keyDown(screen.getByTestId('sampling-dialog-balancing-mode-select'), {
            key: 'Enter'
        });

        expect(screen.getByText('Dictionary (Coming soon)')).toBeInTheDocument();
    });

    it('shows the class target editor in dictionary mode', () => {
        renderClassBalancingForm({ balancingMode: 'dictionary' });

        expect(screen.getByTestId('sampling-class-targets-editor')).toBeInTheDocument();
    });

    it('adds an annotation class target from the dropdown', async () => {
        const onClassTargetsChange = vi.fn();
        renderClassBalancingForm({
            balancingMode: 'dictionary',
            onClassTargetsChange
        });

        await fireEvent.keyDown(screen.getByTestId('sampling-class-target-add-select'), {
            key: 'Enter'
        });
        await fireEvent.pointerUp(await screen.findByTestId('sampling-class-target-option-cat'));

        expect(onClassTargetsChange).toHaveBeenCalledWith({ cat: 1 });
    });

    it('updates an annotation class target weight', async () => {
        const onClassTargetsChange = vi.fn();
        renderClassBalancingForm({
            balancingMode: 'dictionary',
            classTargets: { cat: 1 },
            onClassTargetsChange
        });

        await fireEvent.input(screen.getByTestId('sampling-class-target-input-cat'), {
            target: { value: '0.5' }
        });

        expect(onClassTargetsChange).toHaveBeenCalledWith({ cat: 0.5 });
    });

    it('removes an annotation class target', async () => {
        const onClassTargetsChange = vi.fn();
        renderClassBalancingForm({
            balancingMode: 'dictionary',
            classTargets: { cat: 1, dog: 0.5 },
            onClassTargetsChange
        });

        await fireEvent.click(screen.getByTestId('sampling-class-target-remove-cat'));

        expect(onClassTargetsChange).toHaveBeenCalledWith({ dog: 0.5 });
    });

    it('does not call onClassTargetsChange when input is cleared', async () => {
        const onClassTargetsChange = vi.fn();
        renderClassBalancingForm({
            balancingMode: 'dictionary',
            classTargets: { cat: 1 },
            onClassTargetsChange
        });

        await fireEvent.input(screen.getByTestId('sampling-class-target-input-cat'), {
            target: { value: '' }
        });

        expect(onClassTargetsChange).not.toHaveBeenCalled();
    });
});
