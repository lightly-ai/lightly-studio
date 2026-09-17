import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import { createAnnotationFixture } from '$lib/components/PointCloudLabelingWorkspace/domain/fixtures';
import { createAnnotationDetails } from './pointCloudAnnotationDetails';
import PointCloudAnnotationDetails from './PointCloudAnnotationDetails.svelte';

describe('createAnnotationDetails', () => {
    it('formats location as per-axis strings with fixed precision', () => {
        const details = createAnnotationDetails({
            annotation: {
                ...createAnnotationFixture(),
                center: [10, -2, 1.234]
            }
        });

        expect(details.location).toEqual(['10.00', '-2.00', '1.23']);
    });

    it('formats dimensions as per-axis strings', () => {
        const details = createAnnotationDetails({
            annotation: {
                ...createAnnotationFixture(),
                size: [4.5, 1.8, 1.5]
            }
        });

        expect(details.dimensions).toEqual(['4.50', '1.80', '1.50']);
    });

    it('converts quaternion rotation to euler degrees per axis', () => {
        const details = createAnnotationDetails({
            annotation: {
                ...createAnnotationFixture(),
                rotation: [0, 0, Math.sin(Math.PI / 8), Math.cos(Math.PI / 8)]
            }
        });

        expect(details.rotation).toEqual(['0.0', '0.0', '45.0']);
    });

    it('passes through annotation source id', () => {
        const details = createAnnotationDetails({ annotation: createAnnotationFixture() });

        expect(details.annotationSourceId).toBe('ground-truth');
    });

    it('passes through track id when present', () => {
        const details = createAnnotationDetails({ annotation: createAnnotationFixture() });

        expect(details.trackId).toBe('track-0');
    });

    it('passes through null track id for untracked annotations', () => {
        const details = createAnnotationDetails({
            annotation: { ...createAnnotationFixture(), trackId: null }
        });

        expect(details.trackId).toBeNull();
    });
});

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

const defaultProps = { annotation: defaultAnnotation };

describe('PointCloudAnnotationDetails', () => {
    it('renders location axis values', () => {
        render(PointCloudAnnotationDetails, { props: defaultProps });
        expect(screen.getByText('X 10.00')).toBeInTheDocument();
        expect(screen.getByText('Y -2.00')).toBeInTheDocument();
        expect(screen.getByText('Z 1.23')).toBeInTheDocument();
    });

    it('renders dimension axis values', () => {
        render(PointCloudAnnotationDetails, { props: defaultProps });
        expect(screen.getByText('W 4.50')).toBeInTheDocument();
        expect(screen.getByText('H 1.80')).toBeInTheDocument();
        expect(screen.getByText('D 1.50')).toBeInTheDocument();
    });

    it('renders rotation axis values in degrees', () => {
        render(PointCloudAnnotationDetails, { props: defaultProps });
        expect(screen.getByText('rx 0.0°')).toBeInTheDocument();
        expect(screen.getByText('ry 0.0°')).toBeInTheDocument();
        expect(screen.getByText('rz 45.0°')).toBeInTheDocument();
    });

    it('renders annotation source', () => {
        render(PointCloudAnnotationDetails, { props: defaultProps });
        expect(screen.getByText('ground-truth')).toBeInTheDocument();
    });

    it('renders track ID when present', () => {
        render(PointCloudAnnotationDetails, { props: defaultProps });
        expect(screen.getByText('track-0')).toBeInTheDocument();
    });
});
