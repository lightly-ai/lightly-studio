import { render, screen, within } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import { leaderboardColumns } from '../EvaluationComparison.helpers';
import { makeComparedRun } from '../fixtures';
import EvaluationLeaderboard from './EvaluationLeaderboard.svelte';

const defaultProps = {
    runs: [
        makeComparedRun('yolo-large', { mean_average_precision: 0.512 }),
        makeComparedRun('yolo-small', {
            mean_average_precision: null,
            mean_average_precision_by_iou_threshold: null
        })
    ],
    columns: leaderboardColumns('object_detection'),
    staleRunIds: []
};

describe('EvaluationLeaderboard', () => {
    it('renders the object detection columns and the runs in the given order', () => {
        render(EvaluationLeaderboard, { props: defaultProps });

        const headers = screen.getAllByRole('columnheader').map((cell) => cell.textContent?.trim());
        expect(headers).toEqual(['Run', 'mAP', 'mAP@50', 'mAP@75', 'Precision', 'Recall', 'F1']);
        const [, firstRow, secondRow] = screen.getAllByRole('row');
        expect(firstRow).toHaveTextContent('yolo-large');
        expect(firstRow).toHaveTextContent('0.512');
        expect(secondRow).toHaveTextContent('yolo-small');
    });

    it('shows a dash with a hint for a run without average precision', () => {
        render(EvaluationLeaderboard, { props: defaultProps });

        const secondRow = screen.getAllByRole('row')[2];
        const missingCells = within(secondRow).getAllByTitle('Recompute with average precision');
        expect(missingCells).toHaveLength(3);
        expect(missingCells[0]).toHaveTextContent('—');
    });

    it('marks the best value of each column', () => {
        render(EvaluationLeaderboard, { props: defaultProps });

        const firstRow = screen.getAllByRole('row')[1];
        expect(within(firstRow).getByText('0.512')).toHaveAttribute('data-best', 'true');
    });

    it('shows a badge on a stale run', () => {
        render(EvaluationLeaderboard, { props: { ...defaultProps, staleRunIds: ['yolo-small'] } });

        const secondRow = screen.getAllByRole('row')[2];
        expect(within(secondRow).getByText('Stale')).toBeInTheDocument();
    });
});
