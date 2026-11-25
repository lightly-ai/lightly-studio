import type { WorkflowFile } from '$lib/hooks';

export type WorkflowFileState = WorkflowFile['state'];

/** States the action bar can move a file to. Starting a file is not a button. */
type MoveTarget = 'in_review' | 'accepted' | 'rework';

/** One move the action bar can offer. */
export interface WorkflowAction {
    target: MoveTarget;
    label: string;
    /** Shown while this move waits for the workflow service. */
    pendingLabel: string;
    /** Confirms a successful inline move, before the page moves on to the next sample. */
    doneMessage: string;
    variant: 'default' | 'outline';
    /** Extra button classes, e.g. the red outline of Send back. */
    class?: string;
    /** Asked before an inline move that might be a slip, e.g. submitting an untouched file. */
    confirmation?: WorkflowActionConfirmation;
}

/** What the user confirms before a move that skips a workflow step or might be a slip. */
export interface WorkflowActionConfirmation {
    title: string;
    description: string;
    confirmLabel: string;
}

/** A move offered in the admin menu: always confirmed first. */
export interface WorkflowMenuAction extends WorkflowAction {
    confirmation: WorkflowActionConfirmation;
}

/** Where each allowed move shows up in the action bar. */
export interface WorkflowActionPlacement {
    /** The natural next step for the state, shown as buttons. */
    inline: WorkflowAction[];
    /** Every other allowed move, in the "Admin actions" menu. */
    menu: WorkflowMenuAction[];
}

/** The caller's role on the file, from the workflow service. */
export type WorkflowRole = WorkflowFile['your_role'];

/** The natural next step in each state: what an assigned person sees as inline buttons. */
const INLINE: Record<WorkflowFileState, MoveTarget[]> = {
    not_started: ['in_review'],
    in_progress: ['in_review'],
    in_review: ['rework', 'accepted'],
    rework: ['in_review'],
    accepted: []
};

/** What the labeler confirms before submitting a file they never edited. */
const SUBMIT_UNTOUCHED: WorkflowActionConfirmation = {
    title: 'Submit as-is?',
    description: 'You haven’t made any changes.',
    confirmLabel: 'Submit for review'
};

/** Order of the moves in the admin menu. */
const MENU_ORDER: MoveTarget[] = ['in_review', 'accepted', 'rework'];

const ACTIONS: Record<MoveTarget, WorkflowAction> = {
    in_review: {
        target: 'in_review',
        label: 'Submit for review',
        pendingLabel: 'Submitting…',
        doneMessage: 'Submitted for review',
        variant: 'default'
    },
    accepted: {
        target: 'accepted',
        label: 'Accept',
        pendingLabel: 'Accepting…',
        doneMessage: 'Sample accepted',
        variant: 'default'
    },
    rework: {
        target: 'rework',
        label: 'Send back to Rework',
        pendingLabel: 'Sending back…',
        doneMessage: 'Sent back to Rework',
        variant: 'outline',
        // The red of the Rework state.
        class: 'border-red-500 text-red-500 hover:bg-red-500/10 hover:text-red-500'
    }
};

const REOPEN: WorkflowAction = {
    ...ACTIONS.rework,
    label: 'Reopen (send back to Rework)',
    pendingLabel: 'Reopening…'
};

const ACCEPT_WITHOUT_REVIEW: WorkflowActionConfirmation = {
    title: 'Accept without review?',
    description: 'This skips the reviewer.',
    confirmLabel: 'Accept'
};

/** What each override skips, keyed by `from:target`. Accepting always skips the reviewer. */
const CONFIRMATIONS: Partial<
    Record<`${WorkflowFileState}:${MoveTarget}`, WorkflowActionConfirmation>
> = {
    'not_started:in_review': {
        title: 'Submit for review?',
        description: 'Nobody has labeled this file yet.',
        confirmLabel: 'Submit for review'
    },
    'accepted:rework': {
        title: 'Reopen this file?',
        description: 'It goes back to the labeler for rework.',
        confirmLabel: 'Reopen'
    },
    'in_progress:rework': {
        title: 'Send back to Rework?',
        description: 'The labeler hasn’t submitted yet.',
        confirmLabel: 'Send back to Rework'
    }
};

const actionFor = (from: WorkflowFileState, target: MoveTarget): WorkflowAction =>
    from === 'accepted' && target === 'rework' ? REOPEN : ACTIONS[target];

/** The allowed moves come from the workflow service, so an unexpected one still gets a prompt. */
const confirmationFor = (
    from: WorkflowFileState,
    action: WorkflowAction
): WorkflowActionConfirmation =>
    action.target === 'accepted'
        ? ACCEPT_WITHOUT_REVIEW
        : (CONFIRMATIONS[`${from}:${action.target}`] ?? {
              title: `${action.label}?`,
              description: 'This skips a step of the workflow.',
              confirmLabel: action.label
          });

const isMoveTarget = (state: WorkflowFileState): state is MoveTarget =>
    (MENU_ORDER as WorkflowFileState[]).includes(state);

/**
 * The caller's natural steps. Submitting an untouched file is the labeler's natural step;
 * for an admin it is an override, so it stays in the menu.
 */
const naturalSteps = (state: WorkflowFileState, role: WorkflowRole): MoveTarget[] =>
    state === 'not_started' && role !== 'labeler' ? [] : INLINE[state];

/** An inline button; submitting an untouched file asks first, since it might be a slip. */
const inlineActionFor = (from: WorkflowFileState, target: MoveTarget): WorkflowAction =>
    from === 'not_started'
        ? { ...actionFor(from, target), confirmation: SUBMIT_UNTOUCHED }
        : actionFor(from, target);

/** Splits the moves the user may make into inline buttons and the "Admin actions" menu. */
export function placeWorkflowActions(
    state: WorkflowFileState,
    allowed: WorkflowFileState[],
    role: WorkflowRole
): WorkflowActionPlacement {
    const targets = allowed.filter(isMoveTarget);
    const inline = naturalSteps(state, role).filter((target) => targets.includes(target));
    const menu = MENU_ORDER.filter(
        (target) => targets.includes(target) && !inline.includes(target)
    );
    return {
        inline: inline.map((target) => inlineActionFor(state, target)),
        menu: menu.map((target) => {
            const action = actionFor(state, target);
            return { ...action, confirmation: confirmationFor(state, action) };
        })
    };
}
