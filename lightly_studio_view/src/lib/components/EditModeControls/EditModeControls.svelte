<script lang="ts">
    import Check from '@lucide/svelte/icons/check';
    import LoaderCircle from '@lucide/svelte/icons/loader-circle';
    import Pencil from '@lucide/svelte/icons/pencil';
    import Undo2 from '@lucide/svelte/icons/undo-2';
    import { Button } from '$lib/components';
    import { useEditModeControls } from './useEditModeControls';

    /** Inputs for the undo and edit-mode buttons. */
    interface Props {
        /** Collection reported with the edit analytics events. */
        collectionId: string;
        /** Prefix of the button test ids, unique for each place that shows the buttons. */
        testIdPrefix: string;
    }

    let { collectionId, testIdPrefix }: Props = $props();

    const { isEditingMode, reversibleActions, isUndoing, setEditMode, undo } = useEditModeControls(
        () => collectionId
    );
</script>

{#if $isEditingMode}
    <Button
        icon={$isUndoing ? LoaderCircle : Undo2}
        iconClass={$isUndoing ? 'animate-spin' : undefined}
        buttonProps={{
            onclick: () => undo('click'),
            disabled: $isUndoing || $reversibleActions.length === 0,
            'aria-busy': $isUndoing,
            title: $reversibleActions[0]
                ? `Undo: ${$reversibleActions[0].description}`
                : 'No action to undo',
            'data-testid': `${testIdPrefix}-reverse-action-button`,
            class: 'nav-button'
        }}
    >
        Undo
    </Button>
    <Button
        icon={Check}
        buttonProps={{
            onclick: () => setEditMode(false, 'click'),
            title: 'Finish Editing',
            'data-testid': `${testIdPrefix}-editing-mode-button`,
            class: 'nav-button'
        }}
    >
        Finish Editing
    </Button>
{:else}
    <Button
        icon={Pencil}
        buttonProps={{
            onclick: () => setEditMode(true, 'click'),
            title: 'Edit annotations',
            'data-testid': `${testIdPrefix}-editing-mode-button`,
            class: 'nav-button'
        }}
    >
        Edit annotations
    </Button>
{/if}
