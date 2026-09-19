import { render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
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

const defaultProps = { annotation: defaultAnnotation };

describe('PointCloudAnnotationDetails', () => {
    it('renders annotation metadata', () => {
        render(PointCloudAnnotationDetails, { props: defaultProps });

        expect(screen.getByText('X 10.00')).toBeInTheDocument();
        expect(screen.getByText('Y -2.00')).toBeInTheDocument();
        expect(screen.getByText('Z 1.23')).toBeInTheDocument();

        expect(screen.getByText('W 4.50')).toBeInTheDocument();
        expect(screen.getByText('H 1.80')).toBeInTheDocument();
        expect(screen.getByText('D 1.50')).toBeInTheDocument();

        expect(screen.getByText('rx 0.0°')).toBeInTheDocument();
        expect(screen.getByText('ry 0.0°')).toBeInTheDocument();
        expect(screen.getByText('rz 45.0°')).toBeInTheDocument();

        expect(screen.getByText('ground-truth')).toBeInTheDocument();
        expect(screen.getByText('track-0')).toBeInTheDocument();
    });
});
