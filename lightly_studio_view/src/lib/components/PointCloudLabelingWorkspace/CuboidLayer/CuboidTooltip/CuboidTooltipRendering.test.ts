import { render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import { createAnnotationFixture } from '$lib/components/PointCloudLabelingWorkspace/domain/fixtures';
import CuboidTooltip from './CuboidTooltip.svelte';

const defaultProps = {
    annotation: createAnnotationFixture(),
    annotationClassName: 'Vehicle'
};

describe('CuboidTooltip', () => {
    it('shows the track number when present', () => {
        render(CuboidTooltip, {
            props: { ...defaultProps, annotation: { ...defaultProps.annotation, trackNumber: 0 } }
        });

        expect(screen.getByText('Track number')).toBeInTheDocument();
        expect(screen.getByText('0')).toBeInTheDocument();
    });
});
