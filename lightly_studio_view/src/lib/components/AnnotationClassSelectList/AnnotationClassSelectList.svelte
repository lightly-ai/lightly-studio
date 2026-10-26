<script lang="ts">
    import type { ComponentProps } from 'svelte';
    import { SelectList } from '$lib/components/SelectList';
    import { EditAnnotationClassesButton } from '$lib/components/EditAnnotationClassesButton';

    // A SelectList for annotation classes. Classes are only created in the settings.
    // svelte-ignore custom_element_props_identifier
    let {
        selectedItem = $bindable(),
        ...rest
    }: Omit<ComponentProps<typeof SelectList>, 'allowCreate' | 'footer'> = $props();
</script>

<SelectList bind:selectedItem {...rest} allowCreate={false}>
    {#snippet footer({ close })}
        <EditAnnotationClassesButton onClick={close} />
    {/snippet}
</SelectList>
