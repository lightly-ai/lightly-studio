<script lang="ts">
    import { beforeNavigate, goto } from '$app/navigation';
    import * as Dialog from '$lib/components/ui/dialog';
    import { Button } from '$lib/components/ui/button';
    import { toast } from 'svelte-sonner';
    import type { useLabelWithModel } from '../useLabelWithModel.svelte';

    interface Props {
        labelWithModel: Pick<
            ReturnType<typeof useLabelWithModel>,
            | 'isSaving'
            | 'isGenerating'
            | 'hasUnsavedSuggestions'
            | 'pendingChange'
            | 'requestChange'
            | 'clear'
            | 'confirmChange'
            | 'cancelChange'
        >;
    }

    let { labelWithModel }: Props = $props();
    let allowNavigation = false;

    beforeNavigate((navigation) => {
        if (allowNavigation) {
            allowNavigation = false;
            return;
        }
        if (navigation.to && navigation.to.url.pathname === navigation.from?.url.pathname) return;
        if (labelWithModel.isSaving || labelWithModel.isGenerating) {
            navigation.cancel();
            if (!navigation.willUnload) toast.info('Wait for the current operation to finish.');
            return;
        }
        if (!labelWithModel.hasUnsavedSuggestions) return;
        navigation.cancel();
        // The browser supplies its own confirmation when the document unloads.
        if (navigation.willUnload || !navigation.to) return;
        const destination = navigation.to.url;
        const delta = navigation.delta;
        labelWithModel.requestChange(() => {
            labelWithModel.clear();
            allowNavigation = true;
            if (navigation.type === 'popstate' && delta) history.go(delta);
            else void goto(destination);
        });
    });
</script>

<Dialog.Root
    open={labelWithModel.pendingChange !== null}
    onOpenChange={(open) => {
        if (!open) labelWithModel.cancelChange();
    }}
>
    <Dialog.Content class="max-w-sm">
        <Dialog.Header>
            <Dialog.Title>Discard unsaved suggestions?</Dialog.Title>
            <Dialog.Description>
                Continuing replaces or discards your unsaved suggestions and class corrections.
            </Dialog.Description>
        </Dialog.Header>
        <Dialog.Footer>
            <Button variant="outline" onclick={labelWithModel.cancelChange}>Keep reviewing</Button>
            <Button onclick={labelWithModel.confirmChange}>Discard and continue</Button>
        </Dialog.Footer>
    </Dialog.Content>
</Dialog.Root>
