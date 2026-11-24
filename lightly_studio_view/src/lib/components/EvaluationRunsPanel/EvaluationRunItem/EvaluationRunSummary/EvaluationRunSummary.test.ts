import { render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import EvaluationRunSummary from './EvaluationRunSummary.svelte';

describe('EvaluationRunSummary', () => {
    it('shows the tags that scope the run', () => {
        render(EvaluationRunSummary, {
            props: { groundTruth: 'gt', predictions: 'pred', scopeTagNames: ['vehicles', 'night'] }
        });

        expect(screen.getByTestId('evaluation-run-scope')).toHaveTextContent(
            'Images: vehicles, night'
        );
    });

    it('shows no scope for a run on all images', () => {
        render(EvaluationRunSummary, {
            props: { groundTruth: 'gt', predictions: 'pred', scopeTagNames: [] }
        });

        expect(screen.queryByTestId('evaluation-run-scope')).not.toBeInTheDocument();
    });
});
