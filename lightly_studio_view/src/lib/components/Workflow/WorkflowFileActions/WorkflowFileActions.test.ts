import { fireEvent, render, screen, waitFor, within } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { toast } from 'svelte-sonner';
import type { ComponentProps } from 'svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import WorkflowFileActions from './WorkflowFileActions.svelte';

vi.mock('svelte-sonner', () => ({ toast: { error: vi.fn() } }));

type Props = ComponentProps<typeof WorkflowFileActions>;

/** The admin's allowed moves per state, from the agreed admin matrix. */
const ADMIN_ALLOWED: Record<Props['fileState'], Props['allowedTransitions']> = {
    not_started: ['in_review', 'accepted'],
    in_progress: ['in_review', 'accepted', 'rework'],
    in_review: ['accepted', 'rework'],
    rework: ['in_review', 'accepted'],
    accepted: ['rework']
};

/** A move the workflow service never confirms, to keep the pending state on screen. */
const stuckTransition = () => vi.fn(() => new Promise<void>(() => {}));

const renderActions = (overrides: Partial<Props> = {}) => {
    const props: Props = {
        fileState: 'in_progress',
        allowedTransitions: ['in_review'],
        transitioning: false,
        onTransition: vi.fn().mockResolvedValue(undefined),
        ...overrides
    };
    const result = render(WorkflowFileActions, { props });
    const rerenderWith = (changes: Partial<Props>) => result.rerender({ ...props, ...changes });
    return { onTransition: props.onTransition, rerenderWith };
};

describe('WorkflowFileActions', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        // An open menu from the previous test blocks pointer events on the body.
        document.body.style.pointerEvents = '';
    });

    describe('assigned person', () => {
        it('lets the labeler submit a file in progress for review', async () => {
            const { onTransition } = renderActions();

            await fireEvent.click(screen.getByRole('button', { name: 'Submit for review' }));

            expect(onTransition).toHaveBeenCalledWith('in_review');
            expect(screen.queryByRole('button', { name: 'Accept' })).not.toBeInTheDocument();
        });

        it('shows a loading state and blocks other moves while waiting for the service', async () => {
            const { rerenderWith } = renderActions({ onTransition: stuckTransition() });

            await fireEvent.click(screen.getByRole('button', { name: 'Submit for review' }));
            await rerenderWith({ transitioning: true });

            expect(screen.getByRole('button', { name: 'Submitting…' })).toBeDisabled();
        });

        it('tells the user when the service rejects the move', async () => {
            renderActions({
                onTransition: vi.fn().mockRejectedValue(new Error('Cannot move a file'))
            });

            await fireEvent.click(screen.getByRole('button', { name: 'Submit for review' }));

            await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Cannot move a file'));
        });

        it('lets the labeler resubmit a file in rework', async () => {
            const { onTransition } = renderActions({ fileState: 'rework' });

            await fireEvent.click(screen.getByRole('button', { name: 'Submit for review' }));

            expect(onTransition).toHaveBeenCalledWith('in_review');
        });

        it('offers no action when no move is allowed', () => {
            renderActions({ fileState: 'in_review', allowedTransitions: [] });

            expect(screen.queryByTestId('workflow-file-actions')).not.toBeInTheDocument();
        });

        it('lets the reviewer accept a file in review', async () => {
            const { onTransition } = renderActions({
                fileState: 'in_review',
                allowedTransitions: ['rework', 'accepted']
            });

            await fireEvent.click(screen.getByRole('button', { name: 'Accept' }));

            expect(onTransition).toHaveBeenCalledWith('accepted');
            expect(
                screen.queryByRole('button', { name: 'Submit for review' })
            ).not.toBeInTheDocument();
        });

        it('lets the reviewer send a file back to rework in one click', async () => {
            const { onTransition } = renderActions({
                fileState: 'in_review',
                allowedTransitions: ['rework', 'accepted']
            });

            const sendBack = screen.getByRole('button', { name: 'Send back to Rework' });
            expect(sendBack).toBeEnabled();
            expect(sendBack).toHaveClass('border-red-500', 'text-red-500');
            expect(sendBack).not.toHaveClass('bg-destructive');
            await fireEvent.click(sendBack);

            expect(onTransition).toHaveBeenCalledWith('rework');
        });

        it('shows a loading state on send-back while waiting for the service', async () => {
            const { rerenderWith } = renderActions({
                fileState: 'in_review',
                allowedTransitions: ['rework', 'accepted'],
                onTransition: stuckTransition()
            });

            await fireEvent.click(screen.getByRole('button', { name: 'Send back to Rework' }));
            await rerenderWith({ transitioning: true });

            expect(screen.getByRole('button', { name: 'Sending back…' })).toBeDisabled();
            expect(screen.getByRole('button', { name: 'Accept' })).toBeDisabled();
        });

        it('shows no admin menu when every allowed move is inline', () => {
            renderActions({ fileState: 'in_review', allowedTransitions: ['rework', 'accepted'] });

            expect(screen.queryByRole('button', { name: 'Admin actions' })).not.toBeInTheDocument();
        });
    });

    describe('admin', () => {
        const openMenu = async (user: ReturnType<typeof userEvent.setup>) => {
            await user.click(screen.getByRole('button', { name: 'Admin actions' }));
            return screen.getAllByRole('menuitem').map((item) => item.textContent?.trim());
        };

        it('keeps the natural step inline and puts the other moves in the admin menu', async () => {
            const user = userEvent.setup();
            renderActions({
                fileState: 'in_progress',
                allowedTransitions: ADMIN_ALLOWED.in_progress
            });

            expect(screen.getByRole('button', { name: 'Submit for review' })).toBeInTheDocument();
            expect(await openMenu(user)).toEqual(['Accept', 'Send back to Rework']);
        });

        it('offers only the admin menu on a file nobody has started', async () => {
            const user = userEvent.setup();
            renderActions({
                fileState: 'not_started',
                allowedTransitions: ['in_review', 'accepted']
            });

            expect(screen.getAllByRole('button')).toHaveLength(1);
            expect(await openMenu(user)).toEqual(['Submit for review', 'Accept']);
        });

        it('offers to reopen an accepted file', async () => {
            const user = userEvent.setup();
            renderActions({ fileState: 'accepted', allowedTransitions: ['rework'] });

            expect(await openMenu(user)).toEqual(['Reopen (send back to Rework)']);
        });

        it('names the ⋯ button in a tooltip on hover', async () => {
            const user = userEvent.setup();
            renderActions({ fileState: 'accepted', allowedTransitions: ADMIN_ALLOWED.accepted });

            await user.hover(screen.getByRole('button', { name: 'Admin actions' }));

            expect(await screen.findByRole('tooltip')).toHaveTextContent('Admin actions');
        });

        it('lists only the moves in the menu, without a heading', async () => {
            const user = userEvent.setup();
            renderActions({ fileState: 'accepted', allowedTransitions: ADMIN_ALLOWED.accepted });

            await openMenu(user);

            expect(screen.getByRole('menu')).toHaveTextContent(/^Reopen \(send back to Rework\)$/);
        });

        it('asks before accepting a file that skips review, then accepts it', async () => {
            const user = userEvent.setup();
            const { onTransition } = renderActions({
                fileState: 'not_started',
                allowedTransitions: ['in_review', 'accepted']
            });

            await openMenu(user);
            await user.click(screen.getByRole('menuitem', { name: 'Accept' }));

            const dialog = await screen.findByRole('dialog');
            expect(dialog).toHaveTextContent('Accept without review?');
            expect(dialog).toHaveTextContent('This skips the reviewer.');
            expect(onTransition).not.toHaveBeenCalled();

            await user.click(within(dialog).getByRole('button', { name: 'Accept' }));

            expect(onTransition).toHaveBeenCalledWith('accepted');
            await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
        });

        it('shows progress while a confirmed menu move waits for the service', async () => {
            const user = userEvent.setup();
            renderActions({
                fileState: 'not_started',
                allowedTransitions: ADMIN_ALLOWED.not_started,
                onTransition: stuckTransition()
            });

            await openMenu(user);
            await user.click(screen.getByRole('menuitem', { name: 'Accept' }));
            await user.click(
                within(await screen.findByRole('dialog')).getByRole('button', { name: 'Accept' })
            );

            expect(await screen.findByRole('button', { name: 'Accepting…' })).toBeDisabled();
        });

        it('does nothing when the admin cancels the confirmation', async () => {
            const user = userEvent.setup();
            const { onTransition } = renderActions({
                fileState: 'accepted',
                allowedTransitions: ['rework']
            });

            await openMenu(user);
            await user.click(
                screen.getByRole('menuitem', { name: 'Reopen (send back to Rework)' })
            );
            const dialog = await screen.findByRole('dialog');
            expect(dialog).toHaveTextContent('Reopen this file?');
            expect(dialog).toHaveTextContent('It goes back to the labeler for rework.');

            await user.click(within(dialog).getByRole('button', { name: 'Cancel' }));

            await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
            expect(onTransition).not.toHaveBeenCalled();
        });

        it('asks again after the admin dismissed the confirmation with Escape', async () => {
            const user = userEvent.setup();
            const { onTransition } = renderActions({
                fileState: 'accepted',
                allowedTransitions: ADMIN_ALLOWED.accepted
            });
            const pickReopen = async () => {
                // jsdom never finishes the close animations that give the page its pointer back.
                document.body.style.pointerEvents = '';
                await openMenu(user);
                await user.click(
                    screen.getByRole('menuitem', { name: 'Reopen (send back to Rework)' })
                );
                return screen.findByRole('dialog');
            };

            await pickReopen();
            await user.keyboard('{Escape}');
            await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());

            expect(await pickReopen()).toHaveTextContent('Reopen this file?');
            expect(onTransition).not.toHaveBeenCalled();
        });

        it.each([
            [
                'not_started',
                'Submit for review',
                'Submit for review?',
                'Nobody has labeled this file yet.'
            ],
            [
                'in_progress',
                'Send back to Rework',
                'Send back to Rework?',
                'The labeler hasn’t submitted yet.'
            ],
            ['rework', 'Accept', 'Accept without review?', 'This skips the reviewer.']
        ] as const)(
            'explains what an override from %s to "%s" skips',
            async (fileState, item, title, description) => {
                const user = userEvent.setup();
                renderActions({ fileState, allowedTransitions: ADMIN_ALLOWED[fileState] });

                await openMenu(user);
                await user.click(screen.getByRole('menuitem', { name: item }));

                const dialog = await screen.findByRole('dialog');
                expect(dialog).toHaveTextContent(title);
                expect(dialog).toHaveTextContent(description);
            }
        );
    });
});
