import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { writable } from 'svelte/store';
import WorkspaceClassDialog from './WorkspaceClassDialog.svelte';

vi.mock('$lib/hooks/useCanCreateAnnotationClass/useCanCreateAnnotationClass', () => ({
    useCanCreateAnnotationClass: vi.fn(() => true)
}));

const { controller } = vi.hoisted(() => ({
    controller: {
        current: null as unknown as Record<string, unknown>
    }
}));
vi.mock('../pointCloudWorkspaceLayoutContext.svelte', () => ({
    useWorkspaceControllerContext: () => controller.current
}));

const setTarget = vi.fn();
const handleClassSelected = vi.fn();
const handleClassDialogCancel = vi.fn();

const collection = { id: 'c1' };
const noTrack = { objectTrackId: null, isNewTrack: false };
let names = ['labels', 'preds'];

function setup(target: { targetSource: string | null; needsPick: boolean }) {
    controller.current = {
        editing: {
            showSelectClassDialog: writable(true),
            labels: { data: [{ annotation_label_name: 'car' }] },
            handleClassSelected,
            handleClassDialogCancel,
            getRememberedLabel: () => 'car',
            tracks: { data: [] },
            occupiedTrackIds: new Set()
        },
        data: { annotationSourceNames: names },
        options: {
            get annotationSourceCollectionId() {
                return collection.id;
            }
        },
        targetSource: { ...target, typedSource: null, blockedReason: null, setTarget }
    };
    render(WorkspaceClassDialog);
}

describe('WorkspaceClassDialog', () => {
    beforeAll(() => {
        Element.prototype.scrollIntoView = vi.fn();
    });
    beforeEach(() => {
        vi.clearAllMocks();
        collection.id = 'c1';
        names = ['labels', 'preds'];
    });

    it('asks for a source when none is picked', async () => {
        setup({ targetSource: null, needsPick: true });

        expect(screen.getByTestId('annotation-target-radio-labels')).toHaveAttribute(
            'aria-checked',
            'false'
        );
        expect(screen.getByRole('button', { name: 'Confirm' })).toBeDisabled();
    });

    it('picks the source, then confirms the class', async () => {
        const user = userEvent.setup();
        setup({ targetSource: null, needsPick: true });

        await user.click(screen.getByTestId('annotation-target-radio-preds'));
        const confirm = screen.getByRole('button', { name: 'Confirm' });
        await waitFor(() => expect(confirm).toBeEnabled());
        await user.click(confirm);

        expect(setTarget).toHaveBeenCalledWith('preds', { isNew: false });
        expect(handleClassSelected).toHaveBeenCalledWith('car', noTrack);
        expect(setTarget.mock.invocationCallOrder[0]).toBeLessThan(
            handleClassSelected.mock.invocationCallOrder[0]
        );
    });

    it('preselects the current source', () => {
        setup({ targetSource: 'labels', needsPick: false });

        expect(screen.getByTestId('annotation-target-radio-labels')).toHaveAttribute(
            'aria-checked',
            'true'
        );
    });

    it('does not change the source on cancel', async () => {
        const user = userEvent.setup();
        setup({ targetSource: null, needsPick: true });

        await user.click(screen.getByTestId('annotation-target-radio-preds'));
        await user.click(screen.getByRole('button', { name: 'Cancel' }));

        expect(setTarget).not.toHaveBeenCalled();
        expect(handleClassDialogCancel).toHaveBeenCalled();
    });

    it('picks a new source typed with Enter', async () => {
        const user = userEvent.setup();
        setup({ targetSource: 'labels', needsPick: false });

        await user.type(screen.getByTestId('cuboid-new-source-input'), 'review{Enter}');
        await user.click(screen.getByRole('button', { name: 'Confirm' }));

        expect(setTarget).toHaveBeenCalledWith('review', { isNew: true });
    });

    it('picks a new source typed without Enter before Confirm', async () => {
        const user = userEvent.setup();
        setup({ targetSource: 'labels', needsPick: false });

        await user.type(screen.getByTestId('cuboid-new-source-input'), 'review');
        await user.click(screen.getByRole('button', { name: 'Confirm' }));

        expect(setTarget).toHaveBeenCalledWith('review', { isNew: true });
        expect(handleClassSelected).toHaveBeenCalledWith('car', noTrack);
    });

    it('does not confirm a source that is no longer listed', () => {
        names = ['preds'];
        setup({ targetSource: 'labels', needsPick: false });

        expect(screen.getByRole('button', { name: 'Confirm' })).toBeDisabled();
    });

    it('cancels when the collection changed while the dialog was open', async () => {
        const user = userEvent.setup();
        setup({ targetSource: 'labels', needsPick: false });

        collection.id = 'c2';
        await user.click(screen.getByRole('button', { name: 'Confirm' }));

        expect(setTarget).not.toHaveBeenCalled();
        expect(handleClassSelected).not.toHaveBeenCalled();
        expect(handleClassDialogCancel).toHaveBeenCalled();
    });
});
