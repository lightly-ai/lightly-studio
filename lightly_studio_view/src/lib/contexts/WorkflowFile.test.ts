import { render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { workflowFile } from '$lib/components/Workflow/workflowFile.fixture';
import type { createWorkflowFileContext } from './WorkflowFile.svelte';
import WorkflowFileContextTestWrapper from './WorkflowFileContextTestWrapper.test.svelte';

type Context = ReturnType<typeof createWorkflowFileContext>;

const json = (body: unknown, status = 200) =>
    Promise.resolve(new Response(JSON.stringify(body), { status }));

/** Renders the context for a batch file that is in progress and waits for it to load. */
const renderLoadedContext = async () => {
    let context: Context | undefined;
    render(WorkflowFileContextTestWrapper, {
        props: { onContext: (value) => (context = value) }
    });
    await waitFor(() => expect(screen.getByTestId('probe-state')).toHaveTextContent('in_progress'));
    return context!;
};

describe('createWorkflowFileContext', () => {
    afterEach(() => {
        vi.unstubAllGlobals();
    });

    it('shows the new state only after the service confirmed the move', async () => {
        let state = workflowFile.state;
        let confirm: (response: Response) => void = () => {};
        vi.stubGlobal(
            'fetch',
            vi.fn((url: string) => {
                if (url.endsWith('/transitions')) {
                    return new Promise<Response>((resolve) => {
                        confirm = (response) => {
                            state = 'in_review';
                            resolve(response);
                        };
                    });
                }
                return json({ ...workflowFile, state });
            })
        );
        const context = await renderLoadedContext();

        const transition = context.transition('in_review');
        await waitFor(() => expect(context.transitioning).toBe(true));
        expect(screen.getByTestId('probe-state')).toHaveTextContent('in_progress');

        confirm(new Response('{}'));
        await transition;

        expect(screen.getByTestId('probe-state')).toHaveTextContent('in_review');
        await waitFor(() => expect(context.transitioning).toBe(false));
    });

    it('rejects with the service’s reason and shows the file as the service has it', async () => {
        let state = workflowFile.state;
        vi.stubGlobal(
            'fetch',
            vi.fn((url: string) => {
                if (url.endsWith('/transitions')) {
                    // Another tab submitted the file first.
                    state = 'in_review';
                    return json({ detail: 'Cannot move a file from In review to In review' }, 409);
                }
                return json({ ...workflowFile, state });
            })
        );
        const context = await renderLoadedContext();

        await expect(context.transition('in_review')).rejects.toThrow(
            'Cannot move a file from In review to In review'
        );
        expect(screen.getByTestId('probe-state')).toHaveTextContent('in_review');
    });

    it('fails when the moved file cannot be read again', async () => {
        let moved = false;
        vi.stubGlobal(
            'fetch',
            vi.fn((url: string) => {
                if (url.endsWith('/transitions')) {
                    moved = true;
                    return json({});
                }
                return moved ? json({}, 500) : json(workflowFile);
            })
        );
        const context = await renderLoadedContext();

        await expect(context.transition('in_review')).rejects.toThrow(
            'Could not load the batch context (500)'
        );
    });
});
