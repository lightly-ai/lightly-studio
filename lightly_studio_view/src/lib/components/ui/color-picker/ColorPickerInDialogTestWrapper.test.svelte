<script lang="ts">
    import * as Dialog from '$lib/components/ui/dialog';
    import ColorPicker from './color-picker.svelte';

    interface Props {
        onChange?: (color: string, alpha: number) => void;
    }

    let { onChange }: Props = $props();
</script>

<Dialog.Root open>
    <Dialog.Content aria-label="Host dialog">
        <ColorPicker {onChange}>
            <span>Open color picker</span>
        </ColorPicker>
    </Dialog.Content>
</Dialog.Root>
