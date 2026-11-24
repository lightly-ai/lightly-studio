import { render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import { makeComparedRun } from '../fixtures';
import EvaluationComparisonView from './EvaluationComparisonView.svelte';

describe('EvaluationComparisonView', () => {
    it('ranks the runs by mAP', () => {
        render(EvaluationComparisonView, {
            props: {
                taskType: 'object_detection',
                runs: [
                    makeComparedRun('low', { mean_average_precision: 0.2 }),
                    makeComparedRun('high', { mean_average_precision: 0.9 })
                ]
            }
        });

        const [, firstRow, secondRow] = screen.getAllByRole('row');
        expect(firstRow).toHaveTextContent('high');
        expect(secondRow).toHaveTextContent('low');
    });

    it('warns about runs on different images', () => {
        const otherImages = makeComparedRun('b');
        otherImages.metrics.evaluated_sample_set_hash = 'hash-b';

        render(EvaluationComparisonView, {
            props: { taskType: 'object_detection', runs: [makeComparedRun('a'), otherImages] }
        });

        expect(screen.getByRole('alert')).toHaveTextContent('Runs evaluate different images.');
    });
});
