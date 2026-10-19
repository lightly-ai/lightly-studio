import { render, screen, fireEvent } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import { createAnnotationFixture } from '$lib/components/PointCloudLabelingWorkspace/domain/fixtures';
import PointCloudAnnotationDetails from './PointCloudAnnotationDetails.svelte';

const defaultAnnotation = {
    ...createAnnotationFixture(),
    center: [10, -2, 1.234] as [number, number, number],
    size: [4.5, 1.8, 1.5] as [number, number, number],
    rotation: [0, 0, Math.sin(Math.PI / 8), Math.cos(Math.PI / 8)] as [
        number,
        number,
        number,
        number
    ]
};

const defaultProps = { annotation: defaultAnnotation, annotationSourceName: 'Ground Truth' };

describe('PointCloudAnnotationDetails', () => {
    it('renders annotation metadata', () => {
        render(PointCloudAnnotationDetails, { props: defaultProps });

        expect(screen.getByText('X 10.00')).toBeInTheDocument();
        expect(screen.getByText('Y -2.00')).toBeInTheDocument();
        expect(screen.getByText('Z 1.23')).toBeInTheDocument();

        expect(screen.getByText('L 4.50')).toBeInTheDocument();
        expect(screen.getByText('W 1.80')).toBeInTheDocument();
        expect(screen.getByText('H 1.50')).toBeInTheDocument();

        expect(screen.getByText('rx 0.0°')).toBeInTheDocument();
        expect(screen.getByText('ry 0.0°')).toBeInTheDocument();
        expect(screen.getByText('rz 45.0°')).toBeInTheDocument();

        expect(screen.getByText('Ground Truth')).toBeInTheDocument();
        expect(screen.getByText('Track number:')).toBeInTheDocument();
        expect(screen.getByText('7')).toBeInTheDocument();
    });

    it('shows track number 0', () => {
        render(PointCloudAnnotationDetails, {
            props: { annotation: { ...defaultAnnotation, trackNumber: 0 } }
        });

        expect(screen.getByText('Track number:')).toBeInTheDocument();
        expect(screen.getByText('0')).toBeInTheDocument();
    });
});

describe('PointCloudAnnotationDetails - editable mode', () => {
    const defaultEditableProps = {
        annotation: defaultAnnotation,
        annotationSourceName: 'Ground Truth',
        editable: true
    };

    it('renders inputs for location, dimensions, and rotation', () => {
        render(PointCloudAnnotationDetails, { props: defaultEditableProps });

        expect(screen.getByRole('spinbutton', { name: 'location x' })).toBeInTheDocument();
        expect(screen.getByRole('spinbutton', { name: 'location y' })).toBeInTheDocument();
        expect(screen.getByRole('spinbutton', { name: 'location z' })).toBeInTheDocument();
        expect(screen.getByRole('spinbutton', { name: 'dimension l' })).toBeInTheDocument();
        expect(screen.getByRole('spinbutton', { name: 'dimension w' })).toBeInTheDocument();
        expect(screen.getByRole('spinbutton', { name: 'dimension h' })).toBeInTheDocument();
        expect(screen.getByRole('spinbutton', { name: 'rotation rx' })).toBeInTheDocument();
        expect(screen.getByRole('spinbutton', { name: 'rotation ry' })).toBeInTheDocument();
        expect(screen.getByRole('spinbutton', { name: 'rotation rz' })).toBeInTheDocument();
    });

    it('shows full-precision values in location inputs', () => {
        render(PointCloudAnnotationDetails, { props: defaultEditableProps });

        expect(screen.getByRole('spinbutton', { name: 'location x' })).toHaveValue(10);
        expect(screen.getByRole('spinbutton', { name: 'location y' })).toHaveValue(-2);
        expect(screen.getByRole('spinbutton', { name: 'location z' })).toHaveValue(1.234);
    });

    it('annotation source and track number remain visible', () => {
        render(PointCloudAnnotationDetails, { props: defaultEditableProps });

        expect(screen.getByText('Ground Truth')).toBeInTheDocument();
        expect(screen.getByText('Track number:')).toBeInTheDocument();
    });

    it('fires onAnnotationChange with updated center on blur', () => {
        const onAnnotationChange = vi.fn();
        render(PointCloudAnnotationDetails, {
            props: { ...defaultEditableProps, onAnnotationChange }
        });

        const input = screen.getByRole('spinbutton', { name: 'location x' });
        fireEvent.focus(input);
        fireEvent.input(input, { target: { value: '5' } });
        fireEvent.blur(input);

        expect(onAnnotationChange).toHaveBeenCalledWith(
            expect.objectContaining({ center: [5, -2, 1.234] })
        );
    });

    it('fires onAnnotationChange when Enter is pressed', () => {
        const onAnnotationChange = vi.fn();
        render(PointCloudAnnotationDetails, {
            props: { ...defaultEditableProps, onAnnotationChange }
        });

        const input = screen.getByRole('spinbutton', { name: 'location y' });
        // Use input.focus() to actually move jsdom's active element so that
        // the handler's .blur() call correctly dispatches the blur event.
        input.focus();
        fireEvent.input(input, { target: { value: '3' } });
        fireEvent.keyDown(input, { key: 'Enter' });

        expect(onAnnotationChange).toHaveBeenCalledWith(
            expect.objectContaining({ center: [10, 3, 1.234] })
        );
    });

    it('does not fire onAnnotationChange for empty input', () => {
        const onAnnotationChange = vi.fn();
        render(PointCloudAnnotationDetails, {
            props: { ...defaultEditableProps, onAnnotationChange }
        });

        const input = screen.getByRole('spinbutton', { name: 'location x' });
        fireEvent.focus(input);
        fireEvent.input(input, { target: { value: '' } });
        fireEvent.blur(input);

        expect(onAnnotationChange).not.toHaveBeenCalled();
    });

    it('does not fire onAnnotationChange for dimension below minimum', () => {
        const onAnnotationChange = vi.fn();
        render(PointCloudAnnotationDetails, {
            props: { ...defaultEditableProps, onAnnotationChange }
        });

        const input = screen.getByRole('spinbutton', { name: 'dimension l' });
        fireEvent.focus(input);
        fireEvent.input(input, { target: { value: '0.005' } });
        fireEvent.blur(input);

        expect(onAnnotationChange).not.toHaveBeenCalled();
    });
});
