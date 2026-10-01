import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import { createAnnotationFixture } from '$lib/components/PointCloudLabelingWorkspace/domain/fixtures';
import PointCloudRightSidePanel from './PointCloudRightSidePanel.svelte';

const defaultProps = {
    cuboids: [],
    annotationClasses: [{ id: 'vehicle', name: 'Vehicle', color: '#3b82f6' }],
    annotationSources: [{ id: 'ground-truth', name: 'Ground Truth' }],
    selectedCuboidId: null
};

describe('PointCloudRightSidePanel', () => {
    it('shows the empty message when there are no cuboids', () => {
        render(PointCloudRightSidePanel, { props: defaultProps });

        expect(screen.getByText('No annotations')).toBeInTheDocument();
    });

    it('renders a row for each cuboid', () => {
        const cuboid = createAnnotationFixture();
        render(PointCloudRightSidePanel, { props: { ...defaultProps, cuboids: [cuboid] } });

        expect(screen.getAllByTestId('point-cloud-annotation-list-row')).toHaveLength(1);
    });
});
