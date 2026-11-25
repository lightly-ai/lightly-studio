import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { createRawSnippet } from 'svelte';
import { get, writable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import DetailsHeader from './DetailsHeader.svelte';
import { workflowFile } from '$lib/components/Workflow/workflowFile.fixture';
import type { useWorkflowFileContext } from '$lib/contexts/WorkflowFile.svelte';

const mocks = vi.hoisted(() => ({
    role: 'labeler',
    isEditingMode: undefined as unknown as import('svelte/store').Writable<boolean>,
    workflow: undefined as
        | Partial<NonNullable<ReturnType<typeof useWorkflowFileContext>>>
        | undefined
}));

vi.mock('$lib/hooks', async () => {
    const { writable } = await import('svelte/store');
    return {
        useGlobalStorage: () => ({
            isEditingMode: mocks.isEditingMode,
            setIsEditingMode: (value: boolean) => mocks.isEditingMode.set(value),
            reversibleActions: writable([]),
            executeReversibleAction: vi.fn()
        }),
        useOperatorsDialog: () => ({ openOperatorsDialog: vi.fn() }),
        useSettings: () => ({ settingsStore: writable({ key_toggle_edit_mode: 'e' }) }),
        usePostHog: () => ({ trackEvent: vi.fn() })
    };
});
vi.mock('$lib/hooks/useGlobalStorage', () => ({
    useGlobalStorage: () => ({
        isSampleDetailsSidePanelCollapsed: writable(false),
        toggleSampleDetailsSidePanelCollapsed: vi.fn()
    })
}));
vi.mock('$lib/hooks/useSettingsDialog/useSettingsDialog', () => ({
    useSettingsDialog: () => ({ openSettingsDialog: vi.fn() })
}));
vi.mock('$lib/hooks/useAuth/useAuth', () => ({
    default: () => ({ user: { role: mocks.role } })
}));
vi.mock('$lib/contexts/WorkflowFile.svelte', () => ({
    useWorkflowFileContext: () => mocks.workflow
}));

const breadcrumb = createRawSnippet(() => ({
    render: () => '<nav data-testid="test-breadcrumb">Dataset / Sample</nav>'
}));
const extraActions = createRawSnippet(() => ({
    render: () => '<button type="button">Enter fullscreen</button>'
}));

const renderHeader = (props: Record<string, unknown> = {}) =>
    render(DetailsHeader, { props: { collectionId: 'collection-1', breadcrumb, ...props } });

describe('DetailsHeader', () => {
    beforeEach(() => {
        mocks.isEditingMode = writable(false);
        mocks.workflow = undefined;
        mocks.role = 'labeler';
    });

    it('shows the breadcrumb, edit actions and side-panel toggle outside a batch', () => {
        // Plugins and Settings show from the editor role up.
        mocks.role = 'editor';
        renderHeader();

        expect(screen.getByTestId('test-breadcrumb')).toBeInTheDocument();
        expect(screen.getByTestId('breadcrumb-edit-button')).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Plugins' })).toBeInTheDocument();
        expect(screen.getByTestId('side-panel-toggle')).toBeInTheDocument();
        expect(screen.queryByTestId('workflow-file-status')).not.toBeInTheDocument();
        expect(screen.queryByTestId('workflow-file-actions')).not.toBeInTheDocument();
        expect(screen.queryByRole('status')).not.toBeInTheDocument();
        expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });

    it('shows the batch file’s status and lets the labeler submit it and move on', async () => {
        const transition = vi.fn().mockResolvedValue(undefined);
        const goToNext = vi.fn();
        mocks.workflow = {
            active: true,
            canEdit: true,
            isError: false,
            transitioning: false,
            transition,
            goToNext,
            file: workflowFile
        };

        renderHeader();

        expect(screen.getByTestId('workflow-state-badge')).toHaveTextContent('In progress');
        await fireEvent.click(screen.getByRole('button', { name: 'Submit for review' }));
        expect(transition).toHaveBeenCalledWith('in_review');
        await waitFor(() => expect(goToNext).toHaveBeenCalledOnce());
    });

    it('offers an unassigned admin the moves the workflow service allows', () => {
        mocks.workflow = {
            active: true,
            canEdit: false,
            isError: false,
            transitioning: false,
            transition: vi.fn().mockResolvedValue(undefined),
            file: {
                ...workflowFile,
                your_role: null,
                can_edit: false,
                allowed_transitions: ['in_review', 'rework', 'accepted']
            }
        };

        renderHeader();

        expect(screen.getByRole('button', { name: 'Submit for review' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Admin actions' })).toBeInTheDocument();
    });

    it('shows extra actions between the edit actions and the side-panel toggle', () => {
        mocks.role = 'editor';
        renderHeader({ extraActions });

        const fullscreen = screen.getByRole('button', { name: 'Enter fullscreen' });
        const settings = screen.getByRole('button', { name: 'Settings' });
        const toggle = screen.getByTestId('side-panel-toggle');
        expect(settings.compareDocumentPosition(fullscreen)).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
        expect(fullscreen.compareDocumentPosition(toggle)).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
    });

    it('can hide the side-panel toggle', () => {
        renderHeader({ showSidePanelToggle: false });

        expect(screen.queryByTestId('side-panel-toggle')).not.toBeInTheDocument();
    });

    it('explains why a submitted file is read-only', () => {
        mocks.workflow = {
            active: true,
            canEdit: false,
            isError: false,
            transitioning: false,
            file: { ...workflowFile, state: 'in_review', can_edit: false }
        };

        renderHeader();

        expect(screen.getByRole('status')).toHaveTextContent(
            'You submitted this file. It’s read-only while marta@example.com reviews it.'
        );
    });

    it('keeps the file read-only when the batch cannot be loaded', () => {
        mocks.workflow = { active: true, canEdit: false, isError: true };

        renderHeader();

        expect(screen.getByRole('alert')).toHaveTextContent(
            'Could not load the batch for this file. It stays read-only.'
        );
    });

    it('shows only the breadcrumb and extra actions when compact, keeping the edit shortcut', async () => {
        mocks.workflow = {
            active: true,
            canEdit: true,
            isError: false,
            transitioning: false,
            file: workflowFile
        };

        renderHeader({ extraActions, compact: true });

        expect(screen.getByTestId('test-breadcrumb')).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Enter fullscreen' })).toBeInTheDocument();
        expect(screen.queryByRole('button', { name: 'Plugins' })).not.toBeInTheDocument();
        expect(screen.queryByRole('button', { name: 'Settings' })).not.toBeInTheDocument();
        expect(screen.getByTestId('breadcrumb-edit-button')).not.toBeVisible();
        expect(screen.queryByTestId('side-panel-toggle')).not.toBeInTheDocument();
        expect(screen.queryByTestId('workflow-file-status')).not.toBeInTheDocument();
        expect(screen.queryByTestId('workflow-file-actions')).not.toBeInTheDocument();

        await fireEvent.keyDown(window, { key: 'e' });
        expect(get(mocks.isEditingMode)).toBe(true);
    });
});
