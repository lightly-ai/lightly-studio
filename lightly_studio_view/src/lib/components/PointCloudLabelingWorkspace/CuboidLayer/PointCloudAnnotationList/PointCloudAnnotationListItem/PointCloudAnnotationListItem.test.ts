import { render, screen, fireEvent } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import { createAnnotationFixture } from '$lib/components/PointCloudLabelingWorkspace/domain/fixtures';
import PointCloudAnnotationListItem from './PointCloudAnnotationListItem.svelte';

const cuboid = createAnnotationFixture();

const defaultProps = {
    cuboid,
    color: '#3366ff',
    className: 'Vehicle',
    isSelected: false,
    onToggle: vi.fn()
};

describe('PointCloudAnnotationListItem', () => {
    it('renders the class name and toggle button', () => {
        render(PointCloudAnnotationListItem, { props: defaultProps });

        expect(screen.getByText('Vehicle')).toBeInTheDocument();
        expect(screen.getByRole('button')).toBeInTheDocument();
    });

    it('calls onToggle with the cuboid id when the row is clicked', () => {
        const onToggle = vi.fn();
        render(PointCloudAnnotationListItem, { props: { ...defaultProps, onToggle } });

        fireEvent.click(screen.getByRole('button'));

        expect(onToggle).toHaveBeenCalledWith(cuboid.id);
    });

    it('does not show annotation details when not selected', () => {
        render(PointCloudAnnotationListItem, { props: defaultProps });

        expect(screen.queryByTestId('point-cloud-annotation-details')).not.toBeInTheDocument();
    });

    it('shows annotation details when selected', () => {
        render(PointCloudAnnotationListItem, {
            props: { ...defaultProps, isSelected: true }
        });

        expect(screen.getByTestId('point-cloud-annotation-details')).toBeInTheDocument();
    });

    it('calls onCuboidTransform with the geometry change when annotation is committed', async () => {
        const onCuboidTransform = vi.fn();
        render(PointCloudAnnotationListItem, {
            props: { ...defaultProps, isSelected: true, editable: true, onCuboidTransform }
        });

        const input = screen.getByRole('spinbutton', { name: 'location x' });
        fireEvent.focus(input);
        fireEvent.input(input, { target: { value: '99' } });
        fireEvent.blur(input);

        expect(onCuboidTransform).toHaveBeenCalledWith(
            expect.objectContaining({
                annotationId: cuboid.id,
                frameId: cuboid.frameId,
                center: [99, -2, 1]
            })
        );
    });
});
