<script module lang="ts">
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import { expect, fn, screen, userEvent, within } from 'storybook/test';
    import WorkflowFileActions from './WorkflowFileActions.svelte';

    /** How long a story's move takes, so the pending label shows. */
    const MOVE_DELAY_MS = 1500;

    /** Resolves after a short delay, so the pending label shows. */
    const slowTransition = () =>
        fn(() => new Promise<void>((resolve) => setTimeout(resolve, MOVE_DELAY_MS)));

    /** A move that never finishes, to keep the pending state on screen. */
    const stuckTransition = () => fn(() => new Promise<void>(() => {}));

    const { Story } = defineMeta({
        title: 'Workflow/WorkflowFileActions',
        component: WorkflowFileActions,
        tags: ['autodocs'],
        parameters: { layout: 'centered' },
        argTypes: {
            fileState: {
                control: 'select',
                options: ['not_started', 'in_progress', 'in_review', 'rework', 'accepted']
            },
            allowedTransitions: {
                control: 'check',
                options: ['in_review', 'accepted', 'rework']
            }
        },
        args: { transitioning: false }
    });

    const openAdminMenu = async (canvasElement: HTMLElement) => {
        await userEvent.click(within(canvasElement).getByRole('button', { name: 'Admin actions' }));
        await screen.findByRole('menu');
    };
</script>

<!-- Assigned people: what they see today. -->

<Story
    name="Labeler / In progress"
    args={{
        fileState: 'in_progress',
        allowedTransitions: ['in_review'],
        onTransition: slowTransition()
    }}
/>

<Story
    name="Labeler / Rework"
    args={{
        fileState: 'rework',
        allowedTransitions: ['in_review'],
        onTransition: slowTransition()
    }}
/>

<Story
    name="Reviewer / In review"
    args={{
        fileState: 'in_review',
        allowedTransitions: ['rework', 'accepted'],
        onTransition: slowTransition()
    }}
/>

<!-- Admins: the natural step inline, every other allowed move in the ⋯ menu. -->

<Story
    name="Admin / Not started"
    args={{
        fileState: 'not_started',
        allowedTransitions: ['in_review', 'accepted'],
        onTransition: slowTransition()
    }}
    play={async ({ canvasElement }) => openAdminMenu(canvasElement)}
/>

<Story
    name="Admin / In progress"
    args={{
        fileState: 'in_progress',
        allowedTransitions: ['in_review', 'accepted', 'rework'],
        onTransition: slowTransition()
    }}
    play={async ({ canvasElement }) => openAdminMenu(canvasElement)}
/>

<Story
    name="Admin / In review"
    args={{
        fileState: 'in_review',
        allowedTransitions: ['rework', 'accepted'],
        onTransition: slowTransition()
    }}
/>

<Story
    name="Admin / Rework"
    args={{
        fileState: 'rework',
        allowedTransitions: ['in_review', 'accepted'],
        onTransition: slowTransition()
    }}
    play={async ({ canvasElement }) => openAdminMenu(canvasElement)}
/>

<Story
    name="Admin / Accepted"
    args={{
        fileState: 'accepted',
        allowedTransitions: ['rework'],
        onTransition: slowTransition()
    }}
    play={async ({ canvasElement }) => openAdminMenu(canvasElement)}
/>

<Story
    name="Admin / Confirm accept on a file nobody started"
    args={{
        fileState: 'not_started',
        allowedTransitions: ['in_review', 'accepted'],
        onTransition: slowTransition()
    }}
    play={async ({ canvasElement }) => {
        await openAdminMenu(canvasElement);
        await userEvent.click(screen.getByRole('menuitem', { name: 'Accept' }));
        await expect(await screen.findByRole('dialog')).toHaveTextContent('Accept without review?');
    }}
/>

<Story
    name="Pending move"
    args={{
        fileState: 'in_review',
        allowedTransitions: ['rework', 'accepted'],
        onTransition: stuckTransition()
    }}
    play={async ({ canvasElement }) => {
        await userEvent.click(within(canvasElement).getByRole('button', { name: 'Accept' }));
    }}
/>
