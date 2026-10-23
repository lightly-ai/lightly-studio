<script lang="ts">
    import type { SettingsDialogState } from '../settingsDialogState.svelte';
    import { generalShortcuts, staticToolShortcuts, toolShortcuts } from '../settingsDialogConfig';
    import { SettingsGroup } from '../SettingsGroup';
    import { ShortcutSettingRow } from '../ShortcutSettingRow';

    interface Props {
        dialogState: SettingsDialogState;
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

<div class="space-y-5">
    <SettingsGroup title="General" columns={2}>
        {@render recordableRows(generalShortcuts)}
    </SettingsGroup>
    <SettingsGroup title="Annotation tools" columns={2}>
        {@render recordableRows(toolShortcuts)}
        {#each staticToolShortcuts as setting (setting.id)}
            <ShortcutSettingRow
                id={setting.id}
                label={setting.label}
                value={setting.displayValue}
                isRecording={false}
                disabled
            />
        {/each}
    </SettingsGroup>
</div>
