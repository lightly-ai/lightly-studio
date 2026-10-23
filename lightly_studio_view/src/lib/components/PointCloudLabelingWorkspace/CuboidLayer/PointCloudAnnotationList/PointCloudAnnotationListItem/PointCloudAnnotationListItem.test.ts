import { render, screen, fireEvent } from '@testing-library/svelte';
import { describe, expect, it, vi, type Mock } from 'vitest';
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

    it('uses the current annotation prop as base after a viewport drag updates the geometry', async () => {
        const onCuboidTransform: Mock = vi.fn();
        const { rerender } = render(PointCloudAnnotationListItem, {
            props: { ...defaultProps, isSelected: true, editable: true, onCuboidTransform }
        });

        // Panel sets X=99 and commits.
        const xInput = screen.getByRole('spinbutton', { name: 'location x' });
        fireEvent.focus(xInput);
        fireEvent.input(xInput, { target: { value: '99' } });
        fireEvent.blur(xInput);

        // Viewport drag updates the annotation prop (as $annotations would after transforms.commit).
        const draggedCuboid = { ...cuboid, center: [-20.69, 12.12, 0] as [number, number, number] };
        await rerender({
            ...defaultProps,
            cuboid: draggedCuboid,
            isSelected: true,
            editable: true,
            onCuboidTransform
        });

        // Second panel commit: L=12. Must build from drag geometry, not the first panel commit.
        const lInput = screen.getByRole('spinbutton', { name: 'dimension l' });
        fireEvent.focus(lInput);
        fireEvent.input(lInput, { target: { value: '12' } });
        fireEvent.blur(lInput);

        expect(onCuboidTransform).toHaveBeenLastCalledWith(
            expect.objectContaining({
                center: [-20.69, 12.12, 0],
                size: [12, cuboid.size[1], cuboid.size[2]]
            })
        );
    });
});
