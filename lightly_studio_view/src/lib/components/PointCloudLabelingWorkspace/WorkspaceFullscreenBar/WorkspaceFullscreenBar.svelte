<script lang="ts">
    import { page } from '$app/state';
    import { Logo } from '$lib/components';
    import { EditModeControls } from '$lib/components/EditModeControls';
    import { hasMinimumRole, useAuth } from '$lib/hooks';

    // The app header is outside the fullscreen element, so the browser does not show it.
    // This bar shows the app header controls that labeling needs in fullscreen.
    const { user } = useAuth();
    const canEdit = hasMinimumRole(user?.role, 'labeler');
</script>

<header
    class="mb-3 flex shrink-0 items-center justify-between border-b border-border-hard bg-card px-4 py-4 pl-8 text-diffuse-foreground"
    data-testid="workspace-fullscreen-bar"
>
    <Logo />
    {#if canEdit}
        <div class="flex items-center gap-2">
            <EditModeControls
                collectionId={page.params.collection_id ?? ''}
                testIdPrefix="workspace-fullscreen"
            />
        </div>
    {/if}
</header>
