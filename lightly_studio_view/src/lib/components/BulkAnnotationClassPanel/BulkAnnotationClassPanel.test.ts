import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import BulkAnnotationClassPanel from './BulkAnnotationClassPanel.svelte';

const onApply = vi.fn();
const onSourceChange = vi.fn();

const defaultProps = {
    selectedCount: 10,
    annotationClasses: [
        { id: '1', name: 'dog' },
        { id: '2', name: 'cat' }
    ],
    annotationSources: ['ground_truth', 'predictions'],
    selectedSource: 'ground_truth',
    selectionClassCounts: [{ className: 'dog', sampleCount: 3 }],
    isLoadingCounts: false,
    isApplying: false,
    onSourceChange,
    onApply
};

const pickClass = async (user: ReturnType<typeof userEvent.setup>, name: string) => {
    await user.click(screen.getByTestId('bulk-class-picker-trigger'));
    await user.click(await screen.findByTestId(`bulk-class-picker-option-${name}`));
};

describe('BulkAnnotationClassPanel', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        Element.prototype.scrollIntoView = vi.fn();
    });

    it('renders nothing without a selection', () => {
        render(BulkAnnotationClassPanel, { props: { ...defaultProps, selectedCount: 0 } });

        expect(screen.queryByTestId('bulk-annotation-class-panel')).not.toBeInTheDocument();
    });

    it('shows the selection size, the target source on the action, and the existing classes', () => {
        render(BulkAnnotationClassPanel, { props: defaultProps });

        expect(screen.getByText('Selected images: 10')).toBeInTheDocument();
        expect(screen.getByTestId('bulk-annotation-class-apply')).toHaveTextContent(
            'Add annotation class to ground_truth'
        );
        expect(screen.getByTestId('existing-class-counts')).toHaveTextContent('dog');
    });

    it('shows a loading state for the existing classes', () => {
        render(BulkAnnotationClassPanel, { props: { ...defaultProps, isLoadingCounts: true } });

        expect(screen.getByTestId('existing-class-counts-loading')).toBeInTheDocument();
    });

    it('reports a picked annotation source', async () => {
        const user = userEvent.setup();
        render(BulkAnnotationClassPanel, { props: defaultProps });

        await user.click(screen.getByTestId('bulk-source-picker-trigger'));
        await user.click(await screen.findByTestId('bulk-source-picker-option-predictions'));

        expect(onSourceChange).toHaveBeenCalledWith('predictions');
    });

    it('asks for confirmation before applying and derives the skip count from the counts', async () => {
        const user = userEvent.setup();
        render(BulkAnnotationClassPanel, { props: defaultProps });

        await pickClass(user, 'dog');
        await user.click(screen.getByTestId('bulk-annotation-class-apply'));

        expect(onApply).not.toHaveBeenCalled();
        const dialog = await screen.findByRole('dialog');
        expect(dialog).toHaveTextContent('7 images');
        expect(dialog).toHaveTextContent('ground_truth');
        expect(screen.getByTestId('confirm-apply-skipped')).toHaveTextContent(
            '3 images already have this annotation class and are skipped.'
        );
    });

    it('applies the picked annotation class and source on confirmation', async () => {
        const user = userEvent.setup();
        render(BulkAnnotationClassPanel, { props: defaultProps });

        await pickClass(user, 'cat');
        await user.click(screen.getByTestId('bulk-annotation-class-apply'));
        await user.click(await screen.findByTestId('confirm-apply-submit'));

        expect(onApply).toHaveBeenCalledWith({ className: 'cat', source: 'ground_truth' });
    });

    it('disables the apply action while applying', () => {
        render(BulkAnnotationClassPanel, { props: { ...defaultProps, isApplying: true } });

        expect(screen.getByTestId('bulk-annotation-class-apply')).toBeDisabled();
    });

    it('disables the apply action until an annotation class is picked', () => {
        render(BulkAnnotationClassPanel, { props: defaultProps });

        expect(screen.getByTestId('bulk-annotation-class-apply')).toBeDisabled();
    });
});
