<script lang="ts">
    import { Button } from '$lib/components';
    import { Tooltip } from '$lib/components/ui/tooltip';
    import { useGlobalStorage, useOperatorsDialog, useSettings, usePostHog } from '$lib/hooks';
    import { useSettingsDialog } from '$lib/hooks/useSettingsDialog/useSettingsDialog';
    import useAuth from '$lib/hooks/useAuth/useAuth';
    import { hasMinimumRole } from '$lib/hooks/useAuth/hasMinimumRole';
    import { isInputElement } from '$lib/utils';
    import { Check, Pencil, Puzzle, Settings, Undo2 } from '@lucide/svelte';
    import { get } from 'svelte/store';

    interface Props {
        collectionId: string;
    }

    let { collectionId }: Props = $props();

    const { isEditingMode, setIsEditingMode, reversibleActions, executeReversibleAction } =
        useGlobalStorage();
    const { openOperatorsDialog } = useOperatorsDialog();
    const { openSettingsDialog } = useSettingsDialog();
    const { settingsStore } = useSettings();
    const { user } = useAuth();
    const { trackEvent } = usePostHog();

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
        if (latestAction) {
            trackEvent('edit_undo', {
                collection_id: collectionId,
                triggered_by: triggeredBy
            });
            await executeReversibleAction(latestAction.id);
        }
    };

    const handleKeyDown = (event: KeyboardEvent) => {
        if (isInputElement(event.target)) return;
        if (!canEdit) return;

        if (event.key === get(settingsStore).key_toggle_edit_mode) {
            setEditMode(!$isEditingMode, 'keyboard_shortcut');
        } else if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'z') {
            void executeUndoAction('keyboard_shortcut');
        }
    };

    const undoTooltip = $derived(
        $reversibleActions[0] ? `Undo: ${$reversibleActions[0].description}` : 'No action to undo'
    );
</script>

<svelte:window onkeydown={handleKeyDown} />

<div class="flex items-center gap-1">
    {#if canEdit}
        {#if $isEditingMode}
            <Tooltip content={undoTooltip} position="bottom">
                <Button
                    icon={Undo2}
                    variant="ghost"
                    ariaLabel="Undo"
                    buttonProps={{
                        onclick: () => executeUndoAction('click'),
                        disabled: $reversibleActions.length === 0,
                        'data-testid': 'breadcrumb-undo-button',
                        class: 'h-8 px-2'
                    }}
                />
            </Tooltip>
            <Tooltip content="Finish Editing" position="bottom">
                <Button
                    icon={Check}
                    variant="ghost"
                    ariaLabel="Finish Editing"
                    buttonProps={{
                        onclick: () => setEditMode(false, 'click'),
                        'data-testid': 'breadcrumb-finish-editing-button',
                        class: 'h-8 px-2'
                    }}
                />
            </Tooltip>
        {:else}
            <Tooltip content="Edit annotations" position="bottom">
                <Button
                    icon={Pencil}
                    variant="ghost"
                    ariaLabel="Edit annotations"
                    buttonProps={{
                        onclick: () => setEditMode(true, 'click'),
                        'data-testid': 'breadcrumb-edit-button',
                        class: 'h-8 px-2'
                    }}
                />
            </Tooltip>
        {/if}
    {/if}
    <Tooltip content="Plugins" position="bottom">
        <Button
            icon={Puzzle}
            variant="ghost"
            ariaLabel="Plugins"
            buttonProps={{
                onclick: openOperatorsDialog,
                'data-testid': 'breadcrumb-plugins-button',
                class: 'h-8 px-2'
            }}
        />
    </Tooltip>
    <Tooltip content="Settings" position="bottom">
        <Button
            icon={Settings}
            variant="ghost"
            ariaLabel="Settings"
            buttonProps={{
                onclick: openSettingsDialog,
                'data-testid': 'breadcrumb-settings-button',
                class: 'h-8 px-2'
            }}
        />
    </Tooltip>
</div>
