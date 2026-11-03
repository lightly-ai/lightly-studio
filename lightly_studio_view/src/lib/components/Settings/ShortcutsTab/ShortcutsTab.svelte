<script lang="ts">
    import type { SettingsDialogState } from '../settingsDialogState.svelte';
    import {
        generalShortcuts,
        selectionShortcuts,
        staticGeneralShortcuts,
        staticToolShortcuts,
        toolShortcuts
    } from '../settingsDialogConfig';
    import { SettingsGroup } from '../SettingsGroup';
    import { ShortcutSettingRow } from '../ShortcutSettingRow';

    interface Props {
        dialogState: Pick<
            SettingsDialogState,
            'shortcuts' | 'recordingShortcut' | 'startRecording' | 'shortcutError'
        >;
    }

    const { dialogState }: Props = $props();
</script>

{#snippet recordableRows(settings: typeof generalShortcuts)}
    {#each settings as setting (setting.id)}
        <ShortcutSettingRow
            id={setting.id}
            label={setting.label}
            value={dialogState.shortcuts[setting.key]}
            isRecording={dialogState.recordingShortcut === setting.key}
            onStartRecording={() => dialogState.startRecording(setting.key)}
        />
    {/each}
{/snippet}

{#snippet staticRows(settings: typeof staticToolShortcuts)}
    {#each settings as setting (setting.id)}
        <ShortcutSettingRow
            id={setting.id}
            label={setting.label}
            value={setting.displayValue}
            isRecording={false}
            disabled
        />
    {/each}
{/snippet}

<div class="space-y-8">
    {#if dialogState.shortcutError}
        <p role="alert" class="text-sm text-destructive">{dialogState.shortcutError}</p>
    {/if}
    <SettingsGroup title="General" columns={2}>
        {@render recordableRows(generalShortcuts)}
        {@render staticRows(staticGeneralShortcuts)}
    </SettingsGroup>
    <SettingsGroup title="Annotation tools" columns={2}>
        {@render recordableRows(toolShortcuts)}
        {@render staticRows(staticToolShortcuts)}
    </SettingsGroup>
    <SettingsGroup title="Selection" columns={2}>
        {@render recordableRows(selectionShortcuts)}
    </SettingsGroup>
</div>
