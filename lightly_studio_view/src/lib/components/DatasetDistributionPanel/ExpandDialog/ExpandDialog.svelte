<script lang="ts">
    import * as Dialog from '$lib/components/ui/dialog';
    import { BarChart, type CategoryCount } from '$lib/components/BarChart';

    interface Props {
        /** Two-way bound flag controlling dialog visibility. */
        open: boolean;
        data: CategoryCount[];
        onBarClick?: (item: CategoryCount) => void;
    }

    let { open = $bindable(), data, onBarClick }: Props = $props();
</script>

<Dialog.Root bind:open>
    <Dialog.Content class="flex h-[92vh] max-w-[94vw] flex-col sm:max-w-[94vw]">
        <Dialog.Header>
            <Dialog.Title>Class distribution</Dialog.Title>
            <Dialog.Description>Hover a bar for the full class name and count</Dialog.Description>
        </Dialog.Header>
        <div class="min-h-0 flex-1 overflow-y-auto">
            <BarChart {data} heightPx={560} {onBarClick} />
        </div>
    </Dialog.Content>
</Dialog.Root>
