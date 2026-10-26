<script lang="ts">
    import { Switch } from '$lib/components/ui/switch';
    import { SettingsFieldRow } from '../SettingsFieldRow';

    interface Props {
        id: string;
        label: string;
        description: string;
        checked: boolean;
        disabled: boolean;
    }

    let { id, label, description, checked = $bindable(), disabled }: Props = $props();
</script>

<SettingsFieldRow {id} {label} {description} isLabelClickable>
    <Switch {id} bind:checked {disabled} />
</SettingsFieldRow>
