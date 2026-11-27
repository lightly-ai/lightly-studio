<script lang="ts">
    import { Button } from '$lib/components';
    import { Tooltip } from '$lib/components/ui/tooltip';
    import { useEditModeControls } from '$lib/components/EditModeControls';
    import { useOperatorsDialog, useSettings } from '$lib/hooks';
    import { useSettingsDialog } from '$lib/hooks/useSettingsDialog/useSettingsDialog';
    import useAuth from '$lib/hooks/useAuth/useAuth';
    import { hasMinimumRole } from '$lib/hooks/useAuth/hasMinimumRole';
    import { isInputElement } from '$lib/utils';
    import Check from '@lucide/svelte/icons/check';
    import Pencil from '@lucide/svelte/icons/pencil';
    import Puzzle from '@lucide/svelte/icons/puzzle';
    import Settings from '@lucide/svelte/icons/settings';
    import Undo2 from '@lucide/svelte/icons/undo-2';
    import { get } from 'svelte/store';

    interface Props {
        collectionId: string;
    }

    let { collectionId }: Props = $props();

    const { isEditingMode, reversibleActions, setEditMode, undo } = useEditModeControls(
        () => collectionId
    );
    const { openOperatorsDialog } = useOperatorsDialog();
    const { openSettingsDialog } = useSettingsDialog();
    const { settingsStore } = useSettings();
    const { user } = useAuth();

    const canEdit = $derived(hasMinimumRole(user?.role, 'labeler'));
    const isEditor = $derived(hasMinimumRole(user?.role, 'editor'));

    const handleKeyDown = (event: KeyboardEvent) => {
        if (isInputElement(event.target)) return;
        if (!canEdit) return;

        if (event.key === get(settingsStore).key_toggle_edit_mode) {
            setEditMode(!$isEditingMode, 'keyboard_shortcut');
        } else if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'z') {
            void undo('keyboard_shortcut');
        }
    };

    const latestActionTooltip = $derived(
        $reversibleActions[0] ? `Undo: ${$reversibleActions[0].description}` : ''
    );
    const undoDisabledReason = $derived(
        $reversibleActions.length === 0 ? 'No action to undo' : undefined
    );
</script>

<svelte:window onkeydown={handleKeyDown} />

<div class="flex items-center gap-1">
    {#if canEdit}
        {#if $isEditingMode}
            <Tooltip content={latestActionTooltip} position="bottom" noTriggerRole>
                <Button
                    icon={Undo2}
                    variant="ghost"
                    ariaLabel="Undo"
                    disabledReason={undoDisabledReason}
                    buttonProps={{
                        onclick: () => undo('click'),
                        'data-testid': 'breadcrumb-undo-button',
                        class: 'h-8 px-2'
                    }}
                />
            </Tooltip>
            <Tooltip content="Finish Editing" position="bottom" noTriggerRole>
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
            <Tooltip content="Edit annotations" position="bottom" noTriggerRole>
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
    {#if isEditor}
        <Tooltip content="Plugins" position="bottom" noTriggerRole>
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
        <Tooltip content="Settings" position="bottom" noTriggerRole>
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
    {/if}
</div>
