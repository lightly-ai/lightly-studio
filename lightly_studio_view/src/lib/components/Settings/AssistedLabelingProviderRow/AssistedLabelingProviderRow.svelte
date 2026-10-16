<script lang="ts">
    import { createQuery } from '@tanstack/svelte-query';
    import { listAssistedLabelingProvidersOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
    import { Select } from '$lib/components/Select';
    import { SettingsFieldRow } from '../SettingsFieldRow';

    interface Props {
        value: string;
        disabled?: boolean;
        onValueChange: (value: string) => void;
    }

    const { value, disabled = false, onValueChange }: Props = $props();

    const id = 'assisted-labeling-provider';
    const providersQuery = createQuery(() => listAssistedLabelingProvidersOptions());
    const providers = $derived(providersQuery.data ?? []);
    const selected = $derived(providers.find((p) => p.provider_id === value));
</script>

<SettingsFieldRow {id} label="AI-Assisted Labeling Provider">
    <Select
        items={providers.map((p) => ({ value: p.provider_id, label: p.display_name }))}
        {value}
        {disabled}
        selectProps={{ id }}
        {onValueChange}
    />
</SettingsFieldRow>
{#if selected?.unavailable_reason || selected?.sends_data_to_third_party}
    <div class="grid grid-cols-2 gap-4">
        <div class="col-start-2 space-y-1 text-sm text-muted-foreground">
            {#if selected.unavailable_reason}
                <p>{selected.unavailable_reason}</p>
            {/if}
            {#if selected.sends_data_to_third_party}
                <p>Images are sent to {selected.display_name} for processing.</p>
            {/if}
        </div>
    </div>
{/if}
