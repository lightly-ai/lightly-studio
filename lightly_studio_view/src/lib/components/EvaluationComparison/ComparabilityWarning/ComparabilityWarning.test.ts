import { render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import ComparabilityWarning from './ComparabilityWarning.svelte';

const comparableReport = {
    differentGroundTruth: false,
    differentImageSets: false,
    differentMatchingConfig: false,
    staleRunIds: []
};

describe('ComparabilityWarning', () => {
    it('renders nothing for comparable runs', () => {
        render(ComparabilityWarning, { props: { report: comparableReport } });

        expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });

    it('lists every difference between the runs', () => {
        render(ComparabilityWarning, {
            props: {
                report: {
                    differentGroundTruth: true,
                    differentImageSets: true,
                    differentMatchingConfig: true,
                    staleRunIds: ['run-1']
                }
            }
        });

        const alert = screen.getByRole('alert');
        expect(alert).toHaveTextContent('Runs use different ground truth annotation sources.');
        expect(alert).toHaveTextContent('Runs evaluate different images.');
        expect(alert).toHaveTextContent(
            'Precision, recall and F1 use different matching settings. mAP is not affected.'
        );
        expect(alert).toHaveTextContent(
            'Some runs are stale. Their annotations changed after the evaluation.'
        );
    });
});
