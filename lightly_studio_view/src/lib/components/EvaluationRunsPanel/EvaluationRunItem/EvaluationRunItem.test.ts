import { describe, it, expect, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import type { EvaluationRunView } from '$lib/api/lightly_studio_local/types.gen';
import EvaluationRunItem from './EvaluationRunItem.svelte';

const baseRun: EvaluationRunView = {
    id: 'run-1',
    name: 'Detection eval — v1',
    evaluation_run_configuration: {
        iou_threshold: 0.5,
        split: 'val',
        classwise: true
    },
    created_at: new Date('2026-01-15T10:30:00Z')
};

describe('EvaluationRunItem', () => {
    it('renders the run name and creation date', () => {
        render(EvaluationRunItem, {
            props: { run: baseRun, expanded: false, onToggle: vi.fn() }
        });

        const expectedDate = new Intl.DateTimeFormat('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        }).format(baseRun.created_at);

        expect(screen.getByTestId('evaluation-run-name')).toHaveTextContent('Detection eval — v1');
        expect(screen.getByTestId('evaluation-run-date')).toHaveTextContent(expectedDate);
        expect(screen.getByTestId('evaluation-run-item')).toHaveAttribute('aria-expanded', 'false');
    });

    it('hides configuration details when collapsed', () => {
        render(EvaluationRunItem, {
            props: { run: baseRun, expanded: false, onToggle: vi.fn() }
        });

        expect(screen.queryByTestId('evaluation-run-details')).not.toBeInTheDocument();
    });

    it('renders configuration entries when expanded', () => {
        render(EvaluationRunItem, {
            props: { run: baseRun, expanded: true, onToggle: vi.fn() }
        });

        const details = screen.getByTestId('evaluation-run-details');
        expect(details).toBeInTheDocument();
        expect(details).toHaveTextContent('iou_threshold');
        expect(details).toHaveTextContent('0.5');
        expect(details).toHaveTextContent('split');
        expect(details).toHaveTextContent('val');
        expect(details).toHaveTextContent('classwise');
        expect(details).toHaveTextContent('true');
        expect(screen.getByTestId('evaluation-run-item')).toHaveAttribute('aria-expanded', 'true');
    });

    it('shows a placeholder when configuration is empty', () => {
        const run: EvaluationRunView = { ...baseRun, evaluation_run_configuration: {} };
        render(EvaluationRunItem, {
            props: { run, expanded: true, onToggle: vi.fn() }
        });

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
        render(EvaluationRunItem, {
            props: { run, expanded: true, onToggle: vi.fn() }
        });

        expect(screen.getByTestId('evaluation-run-config')).toHaveTextContent('["cat","dog"]');
    });

    it('shows the metrics placeholder when expanded', () => {
        render(EvaluationRunItem, {
            props: { run: baseRun, expanded: true, onToggle: vi.fn() }
        });

        expect(screen.getByTestId('evaluation-run-details')).toHaveTextContent(
            'Metrics not yet available — backend support pending.'
        );
    });

    it('calls onToggle when the row is clicked', async () => {
        const onToggle = vi.fn();
        render(EvaluationRunItem, {
            props: { run: baseRun, expanded: false, onToggle }
        });

        await fireEvent.click(screen.getByTestId('evaluation-run-item'));
        expect(onToggle).toHaveBeenCalledOnce();
    });
});
