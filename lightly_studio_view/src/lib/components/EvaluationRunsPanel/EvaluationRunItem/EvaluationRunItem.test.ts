import { describe, it, expect, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import type { EvaluationRunView } from '$lib/api/lightly_studio_local/types.gen';
import { formatDate } from '$lib/utils';
import EvaluationRunItem from './EvaluationRunItem.svelte';

vi.mock(
    './EvaluationRunConfusionMatrixSection/EvaluationRunConfusionMatrixSection.svelte',
    async () => {
        const module =
            await import('./EvaluationRunConfusionMatrixSection/EvaluationRunConfusionMatrixSection.mock.svelte');
        return { default: module.default };
    }
);

const baseRun: EvaluationRunView = {
    id: 'run-1',
    name: 'Detection eval — v1',
    evaluation_run_configuration: {
        iou_threshold: 0.5,
        split: 'val',
        classwise: true
    },
    created_at: new Date('2026-01-15T10:30:00Z'),
    gt_annotation_source: 'ground_truth_v1',
    pred_annotation_source: 'predictions_v2'
};

const defaultProps = {
    run: baseRun,
    expanded: false,
    onToggle: vi.fn()
};
const baseRunItemTestId = `evaluation-run-item-${baseRun.name}`;

describe('EvaluationRunItem', () => {
    it('renders the run name and creation date', () => {
        render(EvaluationRunItem, { props: { ...defaultProps } });

        expect(screen.getByTestId('evaluation-run-name')).toHaveTextContent('Detection eval — v1');
        expect(screen.getByTestId('evaluation-run-date')).toHaveTextContent(
            formatDate(baseRun.created_at)
        );
        expect(screen.getByTestId(baseRunItemTestId)).toHaveAttribute('aria-expanded', 'false');
    });

    it('hides configuration details when collapsed', () => {
        render(EvaluationRunItem, { props: { ...defaultProps } });

        expect(screen.queryByTestId('evaluation-run-details')).not.toBeInTheDocument();
    });

    it('renders configuration entries when expanded', () => {
        render(EvaluationRunItem, { props: { ...defaultProps, expanded: true } });

        const details = screen.getByTestId('evaluation-run-details');
        expect(details).toBeInTheDocument();
        expect(details).toHaveTextContent('iou_threshold');
        expect(details).toHaveTextContent('0.5');
        expect(details).toHaveTextContent('split');
        expect(details).toHaveTextContent('val');
        expect(details).toHaveTextContent('classwise');
        expect(details).toHaveTextContent('true');
        expect(screen.getByTestId(baseRunItemTestId)).toHaveAttribute('aria-expanded', 'true');
    });

    it('shows a placeholder when configuration is empty', () => {
        const run: EvaluationRunView = { ...baseRun, evaluation_run_configuration: {} };
        render(EvaluationRunItem, { props: { ...defaultProps, run, expanded: true } });

        expect(screen.queryByTestId('evaluation-run-config')).not.toBeInTheDocument();
        expect(screen.getByTestId('evaluation-run-details')).toHaveTextContent(
            'No configuration recorded.'
        );
    });

    it('serializes nested config values as JSON', () => {
        const run: EvaluationRunView = {
            ...baseRun,
            evaluation_run_configuration: { classes: ['cat', 'dog'] }
        };
        render(EvaluationRunItem, { props: { ...defaultProps, run, expanded: true } });

        expect(screen.getByTestId('evaluation-run-config')).toHaveTextContent('["cat","dog"]');
    });

    it('calls onToggle when the row is clicked', async () => {
        const onToggle = vi.fn();
        render(EvaluationRunItem, { props: { ...defaultProps, onToggle } });

        await fireEvent.click(screen.getByTestId(baseRunItemTestId));
        expect(onToggle).toHaveBeenCalledOnce();
    });

    it('renders the GT and prediction annotation sources when expanded', () => {
        render(EvaluationRunItem, { props: { ...defaultProps, expanded: true } });

        expect(screen.getByTestId('evaluation-run-annotation-sources')).toBeInTheDocument();
        expect(screen.getByTestId('evaluation-run-gt-annotation-source')).toHaveTextContent(
            'ground_truth_v1'
        );
        expect(screen.getByTestId('evaluation-run-prediction-annotation-source')).toHaveTextContent(
            'predictions_v2'
        );
    });
});
