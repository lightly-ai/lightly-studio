import { render, screen, fireEvent } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import PointCloudAnnotationLabel from './PointCloudAnnotationLabel.svelte';

vi.mock('$lib/hooks/useAnnotationLabels/useAnnotationLabels', () => ({
    useAnnotationLabels: vi.fn(() => ({
        data: [
            { annotation_label_name: 'car' },
            { annotation_label_name: 'pedestrian' },
            { annotation_label_name: 'vehicle' }
        ]
    }))
}));

const defaultProps = {
    collectionId: 'collection-1',
    currentLabel: 'vehicle',
    onSelect: vi.fn()
};

describe('PointCloudAnnotationLabel', () => {
    it('displays the current annotation class', () => {
        render(PointCloudAnnotationLabel, { props: defaultProps });

        expect(screen.getByRole('combobox')).toHaveTextContent('vehicle');
    });

    it('calls onSelect with the chosen label name when a class is selected', () => {
        const onSelect = vi.fn();
        render(PointCloudAnnotationLabel, { props: { ...defaultProps, onSelect } });

        fireEvent.click(screen.getByRole('combobox'));
        fireEvent.click(screen.getByRole('option', { name: /car/i }));

        expect(onSelect).toHaveBeenCalledWith('car');
    });

    it('restores the previous label when onSelect rejects', async () => {
        const onSelect = vi.fn().mockRejectedValue(new Error('save failed'));
        render(PointCloudAnnotationLabel, {
            props: { ...defaultProps, currentLabel: 'vehicle', onSelect }
        });

        fireEvent.click(screen.getByRole('combobox'));
        fireEvent.click(screen.getByRole('option', { name: /car/i }));
        await vi.waitFor(() => {
            expect(screen.getByRole('combobox')).toHaveTextContent('vehicle');
        });
    });
});
