import { describe, expect, it } from 'vitest';
import { DATASET_NAV, followsBatchOrder, toWorkflowSampleURL } from './datasetNavigation';

describe('toWorkflowSampleURL', () => {
    it('adds the batch params for a sample in a batch', () => {
        expect(
            toWorkflowSampleURL('/datasets/d/image/c/images/s', {
                project_id: 'p1',
                batch_id: 'b1'
            })
        ).toBe('/datasets/d/image/c/images/s?workflow_project=p1&workflow_batch=b1');
    });

    it('keeps the plain URL for a sample in no batch', () => {
        expect(toWorkflowSampleURL('/datasets/d/image/c/images/s', null)).toBe(
            '/datasets/d/image/c/images/s'
        );
        expect(toWorkflowSampleURL('/datasets/d/image/c/images/s', undefined)).toBe(
            '/datasets/d/image/c/images/s'
        );
    });
});

describe('followsBatchOrder', () => {
    it('steps in batch order in workflow mode without dataset navigation', () => {
        expect(followsBatchOrder({ workflowActive: true, state: {} })).toBe(true);
    });

    it('steps in grid order when the sample was opened from the dataset grid', () => {
        expect(followsBatchOrder({ workflowActive: true, state: { nav: DATASET_NAV } })).toBe(
            false
        );
    });

    it('steps in grid order in normal mode', () => {
        expect(followsBatchOrder({ workflowActive: false, state: {} })).toBe(false);
    });
});
