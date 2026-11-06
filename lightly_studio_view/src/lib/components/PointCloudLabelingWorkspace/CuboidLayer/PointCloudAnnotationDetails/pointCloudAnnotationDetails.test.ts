import { render, screen, fireEvent } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { createAnnotationFixture } from '$lib/components/PointCloudLabelingWorkspace/domain/fixtures';
import PointCloudAnnotationDetails from './PointCloudAnnotationDetails.svelte';

const tracksRef = vi.hoisted(
    () =>
        ({
            current: []
        }) as {
            current: {
                object_track_id: string;
                object_track_number: number;
                annotation_class_name: string | null;
                parent_object_track_id?: string | null;
            }[];
        }
);
const updateAnnotationsRef = vi.hoisted(() => ({ current: vi.fn() }));
const parentTrackPendingRef = vi.hoisted(() => ({ current: false }));

vi.mock(
    '$lib/components/PointCloudLabelingWorkspace/pointCloudWorkspaceLayoutContext.svelte',
    () => ({
        usePointCloudWorkspaceLayoutContext: () => () => ({ datasetId: 'ds-1' })
    })
);
vi.mock('$lib/hooks', () => ({
    useTracks: () => ({ data: tracksRef.current, refetch: vi.fn() }),
    useUpdateAnnotationsMutation: () => ({
        updateAnnotations: (...args: unknown[]) => updateAnnotationsRef.current(...args)
    }),
    useUpdateTrackMutation: () => ({
        updateParentTrack: vi.fn(),
        get isPending() {
            return parentTrackPendingRef.current;
        }
    })
}));

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

    it('annotation source remains visible and shows TrackSelect', () => {
        render(PointCloudAnnotationDetails, { props: defaultEditableProps });

        expect(screen.getByText('Ground Truth')).toBeInTheDocument();
        expect(screen.getAllByTestId('track-select').length).toBeGreaterThanOrEqual(1);
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

    it('does not fire onAnnotationChange when field value is unchanged after focus', () => {
        const onAnnotationChange = vi.fn();
        render(PointCloudAnnotationDetails, {
            props: { ...defaultEditableProps, onAnnotationChange }
        });

        const input = screen.getByRole('spinbutton', { name: 'location x' });
        fireEvent.focus(input);
        fireEvent.blur(input);

        expect(onAnnotationChange).not.toHaveBeenCalled();
    });

    it('does not fire onAnnotationChange for Infinity value', () => {
        const onAnnotationChange = vi.fn();
        render(PointCloudAnnotationDetails, {
            props: { ...defaultEditableProps, onAnnotationChange }
        });

        const input = screen.getByRole('spinbutton', { name: 'location x' });
        fireEvent.focus(input);
        fireEvent.input(input, { target: { value: '1e309' } });
        fireEvent.blur(input);

        expect(onAnnotationChange).not.toHaveBeenCalled();
    });

    it('fires onAnnotationChange with updated size on dimension blur', () => {
        const onAnnotationChange = vi.fn();
        render(PointCloudAnnotationDetails, {
            props: { ...defaultEditableProps, onAnnotationChange }
        });

        const input = screen.getByRole('spinbutton', { name: 'dimension l' });
        fireEvent.focus(input);
        fireEvent.input(input, { target: { value: '8' } });
        fireEvent.blur(input);

        expect(onAnnotationChange).toHaveBeenCalledWith(
            expect.objectContaining({ size: [8, 1.8, 1.5] })
        );
    });

    it('fires onAnnotationChange with updated rotation on rotation blur', () => {
        const onAnnotationChange = vi.fn();
        render(PointCloudAnnotationDetails, {
            props: { ...defaultEditableProps, onAnnotationChange }
        });

        const input = screen.getByRole('spinbutton', { name: 'rotation rz' });
        fireEvent.focus(input);
        fireEvent.input(input, { target: { value: '90' } });
        fireEvent.blur(input);

        expect(onAnnotationChange).toHaveBeenCalledWith(
            expect.objectContaining({
                rotation: expect.arrayContaining([expect.any(Number)])
            })
        );
    });

    it('shows TrackSelect instead of read-only track number', () => {
        render(PointCloudAnnotationDetails, { props: defaultEditableProps });

        expect(screen.getAllByTestId('track-select').length).toBeGreaterThanOrEqual(1);
        expect(screen.queryByText('Track number:')).not.toBeInTheDocument();
    });
});

describe('PointCloudAnnotationDetails - track display', () => {
    it('shows read-only track number when not editable', () => {
        render(PointCloudAnnotationDetails, { props: defaultProps });

        expect(screen.getByText('Track number:')).toBeInTheDocument();
        expect(screen.getByText('7')).toBeInTheDocument();
        expect(screen.queryByTestId('track-select')).not.toBeInTheDocument();
    });
});

describe('PointCloudAnnotationDetails - parent track display', () => {
    it('hides parent track in read mode when no parent exists', () => {
        render(PointCloudAnnotationDetails, {
            props: {
                annotation: { ...defaultAnnotation, parentTrackNumber: null }
            }
        });

        expect(screen.queryByText('Parent track:')).not.toBeInTheDocument();
    });

    it('shows parent track in read mode when a parent exists', () => {
        render(PointCloudAnnotationDetails, {
            props: {
                annotation: {
                    ...defaultAnnotation,
                    parentTrackNumber: 3,
                    parentTrackClassName: 'truck'
                }
            }
        });

        expect(screen.getByText('Parent track:')).toBeInTheDocument();
        expect(screen.getByText('truck - 3')).toBeInTheDocument();
    });

    it('shows parent track without class name in read mode', () => {
        render(PointCloudAnnotationDetails, {
            props: {
                annotation: {
                    ...defaultAnnotation,
                    parentTrackNumber: 5,
                    parentTrackClassName: null
                }
            }
        });

        expect(screen.getByText('Parent track:')).toBeInTheDocument();
        expect(screen.getByText('Track 5')).toBeInTheDocument();
    });

    it('always shows parent track select in edit mode when annotation has a track', () => {
        render(PointCloudAnnotationDetails, {
            props: {
                annotation: { ...defaultAnnotation, parentTrackNumber: null },
                editable: true
            }
        });

        expect(screen.getByText('Parent track:')).toBeInTheDocument();
    });

    it('hides parent track select in edit mode when annotation has no track', () => {
        render(PointCloudAnnotationDetails, {
            props: {
                annotation: { ...defaultAnnotation, trackId: null, parentTrackNumber: null },
                editable: true
            }
        });

        expect(screen.queryByText('Parent track:')).not.toBeInTheDocument();
    });
});

describe('PointCloudAnnotationDetails - occupied track filtering', () => {
    beforeAll(() => {
        Element.prototype.scrollIntoView = vi.fn();
    });

    afterEach(() => {
        tracksRef.current = [];
    });

    it('excludes tracks occupied by other annotations on the same frame', async () => {
        const user = userEvent.setup();
        tracksRef.current = [
            { object_track_id: 'track-0', object_track_number: 7, annotation_class_name: 'car' },
            { object_track_id: 'track-1', object_track_number: 1, annotation_class_name: 'truck' },
            { object_track_id: 'track-2', object_track_number: 2, annotation_class_name: 'bus' }
        ];

        render(PointCloudAnnotationDetails, {
            props: {
                annotation: defaultAnnotation,
                editable: true,
                occupiedTrackIds: new Set(['track-0', 'track-1'])
            }
        });

        await user.click(screen.getAllByTestId('select-list-trigger')[0]);

        const labels = screen.getAllByRole('option').map((o) => o.textContent?.trim());
        expect(labels).toContain('car - 7');
        expect(labels).not.toContain('truck - 1');
        expect(labels).toContain('bus - 2');
    });

    it('shows all tracks when no occupiedTrackIds are provided', async () => {
        const user = userEvent.setup();
        tracksRef.current = [
            { object_track_id: 'track-0', object_track_number: 7, annotation_class_name: 'car' },
            { object_track_id: 'track-1', object_track_number: 1, annotation_class_name: 'truck' }
        ];

        render(PointCloudAnnotationDetails, {
            props: {
                annotation: defaultAnnotation,
                editable: true
            }
        });

        await user.click(screen.getAllByTestId('select-list-trigger')[0]);

        const labels = screen.getAllByRole('option').map((o) => o.textContent?.trim());
        expect(labels).toContain('car - 7');
        expect(labels).toContain('truck - 1');
    });
});

describe('PointCloudAnnotationDetails - track selectors disabled while saving', () => {
    afterEach(() => {
        tracksRef.current = [];
        updateAnnotationsRef.current = vi.fn();
        parentTrackPendingRef.current = false;
    });

    it('disables both track selectors while the track assignment is saving', async () => {
        const user = userEvent.setup();
        let resolveUpdate!: () => void;
        updateAnnotationsRef.current = vi.fn(
            () => new Promise<void>((resolve) => (resolveUpdate = resolve))
        );
        tracksRef.current = [
            { object_track_id: 'track-0', object_track_number: 7, annotation_class_name: 'car' }
        ];

        render(PointCloudAnnotationDetails, {
            props: { annotation: defaultAnnotation, editable: true }
        });

        const triggers = screen.getAllByTestId('select-list-trigger');
        expect(triggers[0]).not.toBeDisabled();
        expect(triggers[1]).not.toBeDisabled();

        await user.click(triggers[0]);
        await user.click(screen.getByRole('option', { name: /No track/ }));

        expect(triggers[0]).toBeDisabled();
        expect(triggers[1]).toBeDisabled();

        resolveUpdate();
        await vi.waitFor(() => {
            expect(triggers[0]).not.toBeDisabled();
            expect(triggers[1]).not.toBeDisabled();
        });
    });

    it('disables both track selectors while the parent track mutation is pending', () => {
        tracksRef.current = [
            { object_track_id: 'track-0', object_track_number: 7, annotation_class_name: 'car' }
        ];
        parentTrackPendingRef.current = true;

        render(PointCloudAnnotationDetails, {
            props: { annotation: defaultAnnotation, editable: true }
        });

        const triggers = screen.getAllByTestId('select-list-trigger');
        expect(triggers[0]).toBeDisabled();
        expect(triggers[1]).toBeDisabled();
    });
});
