import { render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { workflowFile } from '$lib/components/Workflow/workflowFile.fixture';
import { STALE_FILE_MESSAGE } from '$lib/hooks/useWorkflowFile/useWorkflowFile.svelte';
import type { createWorkflowFileContext } from './WorkflowFile.svelte';
import WorkflowFileContextTestWrapper from './WorkflowFileContextTestWrapper.test.svelte';

type Context = ReturnType<typeof createWorkflowFileContext>;

const json = (body: unknown, status = 200) =>
    Promise.resolve(new Response(JSON.stringify(body), { status }));

/** Renders the context for a batch file and waits until it shows the expected state. */
const renderLoadedContext = async (loadedState = 'in_progress') => {
    let context: Context | undefined;
    render(WorkflowFileContextTestWrapper, {
        props: { onContext: (value) => (context = value) }
    });
    await waitFor(() => expect(screen.getByTestId('probe-state')).toHaveTextContent(loadedState));
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

    it('says the file changed and shows it as the service has it, read-only', async () => {
        let state = workflowFile.state;
        vi.stubGlobal(
            'fetch',
            vi.fn((url: string) => {
                if (url.endsWith('/transitions')) {
                    // Another tab submitted the file first.
                    state = 'in_review';
                    return json({ detail: 'Cannot move a file from In review to In review' }, 409);
                }
                const turn = state !== 'in_review';
                return json({ ...workflowFile, state, can_edit: turn, your_turn: turn });
            })
        );
        const context = await renderLoadedContext();

        await expect(context.transition('in_review')).rejects.toThrow(STALE_FILE_MESSAGE);
        expect(screen.getByTestId('probe-state')).toHaveTextContent('in_review');
        expect(context.canEdit).toBe(false);
        expect(context.locked).toBe(true);
    });

    describe('next sample', () => {
        it('opens the next sample the page registered', async () => {
            vi.stubGlobal(
                'fetch',
                vi.fn(() => json(workflowFile))
            );
            const context = await renderLoadedContext();
            const first = vi.fn();
            const second = vi.fn();

            const unregisterFirst = context.registerNext(first);
            context.registerNext(second);
            // A stepper that unmounts after its successor registered leaves the successor in place.
            unregisterFirst();
            context.goToNext();

            expect(first).not.toHaveBeenCalled();
            expect(second).toHaveBeenCalledOnce();
        });

        it('stays on the sample when there is no next sample', async () => {
            vi.stubGlobal(
                'fetch',
                vi.fn(() => json(workflowFile))
            );
            const context = await renderLoadedContext();
            const next = vi.fn();

            context.registerNext(next)();

            expect(() => context.goToNext()).not.toThrow();
            expect(next).not.toHaveBeenCalled();
        });
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

    describe('startWork', () => {
        /** Serves the file in `state` and records every move the context asks for. */
        const stubService = (file: typeof workflowFile) => {
            let state = file.state;
            const moves: string[] = [];
            vi.stubGlobal(
                'fetch',
                vi.fn((url: string, init?: RequestInit) => {
                    if (url.endsWith('/transitions')) {
                        state = JSON.parse(String(init?.body)).state;
                        moves.push(state);
                        return json({});
                    }
                    return json({ ...file, state });
                })
            );
            return moves;
        };

        it('moves a not-started file to in progress when its labeler annotates it', async () => {
            const moves = stubService({ ...workflowFile, state: 'not_started' });
            const context = await renderLoadedContext('not_started');

            await context.startWork(workflowFile.sample_id);

            expect(moves).toEqual(['in_progress']);
            expect(screen.getByTestId('probe-state')).toHaveTextContent('in_progress');
        });

        it.each([
            ['the file was already started', { state: 'in_progress' as const }],
            [
                'the reviewer annotates',
                { state: 'not_started' as const, your_role: 'reviewer' as const }
            ],
            [
                'it is not the user’s turn',
                { state: 'not_started' as const, can_edit: false, your_turn: false }
            ],
            [
                'an unassigned admin annotates',
                {
                    state: 'not_started' as const,
                    your_role: null,
                    can_edit: true,
                    your_turn: false
                }
            ],
            [
                'an admin labeler annotates out of turn',
                { state: 'not_started' as const, can_edit: true, your_turn: false }
            ]
        ])('does nothing when %s', async (_, change) => {
            const moves = stubService({ ...workflowFile, ...change });
            const context = await renderLoadedContext(change.state);

            await context.startWork(workflowFile.sample_id);

            expect(moves).toEqual([]);
        });

        it('does nothing for an annotation on another sample', async () => {
            const moves = stubService({ ...workflowFile, state: 'not_started' });
            const context = await renderLoadedContext('not_started');

            await context.startWork('another-sample');

            expect(moves).toEqual([]);
        });
    });
});
