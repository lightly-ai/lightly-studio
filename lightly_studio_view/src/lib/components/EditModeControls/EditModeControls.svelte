<script lang="ts">
    import { Button } from '$lib/components';
    import { useGlobalStorage, usePostHog } from '$lib/hooks';
    import useAuth from '$lib/hooks/useAuth/useAuth';
    import { hasMinimumRole } from '$lib/hooks/useAuth/hasMinimumRole';
    import { useSettings } from '$lib/hooks/useSettings';
    import { isInputElement } from '$lib/utils';
    import { Check, Pencil, Undo2 } from '@lucide/svelte';
    import { get } from 'svelte/store';

    interface Props {
        collectionId: string;
    }

    const { collectionId }: Props = $props();

    const { settingsStore } = useSettings();
    const { setIsEditingMode, isEditingMode, reversibleActions, executeReversibleAction } =
        useGlobalStorage();
    const { trackEvent } = usePostHog();
    const { user } = useAuth();

    const canEdit = $derived(hasMinimumRole(user?.role, 'labeler'));

    type TriggeredBy = 'click' | 'keyboard_shortcut';

    const setEditMode = (active: boolean, triggeredBy: TriggeredBy) => {
        if (active) {
            trackEvent('edit_mode_started', {
                collection_id: collectionId,
                triggered_by: triggeredBy
            });
        }
        setIsEditingMode(active);
    };

    const executeUndoAction = async (triggeredBy: TriggeredBy) => {
        const latestAction = $reversibleActions[0];
        if (!latestAction) return;
        trackEvent('edit_undo', { collection_id: collectionId, triggered_by: triggeredBy });
        await executeReversibleAction(latestAction.id);
    };

    const handleKeyDown = (event: KeyboardEvent) => {
        if (isInputElement(event.target) || !canEdit) return;
        if (event.key === get(settingsStore).key_toggle_edit_mode) {
            setEditMode(!$isEditingMode, 'keyboard_shortcut');
        } else if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'z') {
            void executeUndoAction('keyboard_shortcut');
        }
    };
</script>

<svelte:window onkeydown={handleKeyDown} />

{#if canEdit}
    {#if $isEditingMode}
        <Button
            icon={Undo2}
            buttonProps={{
                onclick: () => executeUndoAction('click'),
                disabled: $reversibleActions.length === 0,
                title: $reversibleActions[0]?.description ?? 'No action to undo',
                'data-testid': 'header-reverse-action-button',
                class: 'h-[26px] px-2 text-xs'
            }}
        >
            Undo
        </Button>
        <Button
            icon={Check}
            buttonProps={{
                onclick: () => setEditMode(false, 'click'),
                title: 'Finish Editing',
                'data-testid': 'header-editing-mode-button',
                class: 'h-[26px] px-2 text-xs'
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
                'data-testid': 'header-editing-mode-button',
                class: 'h-[26px] px-2 text-xs'
            }}
        >
            Edit annotations
        </Button>
    {/if}
{/if}
