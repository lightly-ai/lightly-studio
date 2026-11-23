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
    variant: 'default' | 'outline';
}

/** What an admin confirms before an override that skips a workflow step. */
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

/** The natural next step in each state: what an assigned person sees as inline buttons. */
const INLINE: Record<WorkflowFileState, MoveTarget[]> = {
    not_started: [],
    in_progress: ['in_review'],
    in_review: ['rework', 'accepted'],
    rework: ['in_review'],
    accepted: []
};

/** Order of the moves in the admin menu. */
const MENU_ORDER: MoveTarget[] = ['in_review', 'accepted', 'rework'];

const ACTIONS: Record<MoveTarget, WorkflowAction> = {
    in_review: {
        target: 'in_review',
        label: 'Submit for review',
        pendingLabel: 'Submitting…',
        variant: 'default'
    },
    accepted: {
        target: 'accepted',
        label: 'Accept',
        pendingLabel: 'Accepting…',
        variant: 'default'
    },
    rework: {
        target: 'rework',
        label: 'Send back to Rework',
        pendingLabel: 'Sending back…',
        variant: 'outline'
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

/** Splits the moves the user may make into inline buttons and the "Admin actions" menu. */
export function placeWorkflowActions(
    state: WorkflowFileState,
    allowed: WorkflowFileState[]
): WorkflowActionPlacement {
    const targets = allowed.filter(isMoveTarget);
    const inline = INLINE[state].filter((target) => targets.includes(target));
    const menu = MENU_ORDER.filter(
        (target) => targets.includes(target) && !inline.includes(target)
    );
    return {
        inline: inline.map((target) => actionFor(state, target)),
        menu: menu.map((target) => {
            const action = actionFor(state, target);
            return { ...action, confirmation: confirmationFor(state, action) };
        })
    };
}
