<script lang="ts">
    import * as Popover from '$lib/components/ui/popover';
    import { Button } from '$lib/components/ui/button';
    import { LogOut } from '@lucide/svelte';
    import { cn } from '$lib/utils/shadcn';
    import { useLogout } from '$lib/hooks/useLogout/useLogout';

    interface Props {
        user: {
            username: string;
            email: string;
            role: string;
        };
    }

    let { user }: Props = $props();
    const { logout } = useLogout();

    // TODO: Use name initials when names become available
    // For now, use first letter of username
    const initial = $derived(user.username[0]?.toUpperCase() ?? '?');
</script>

<Popover.Root>
    <Popover.Trigger>
        {#snippet child({ props })}
            <button
                {...props}
                type="button"
                class={cn(
                    'bg-primary text-primary-foreground hover:bg-primary/90 flex size-10 items-center justify-center rounded-full transition-colors',
                    'focus-visible:ring-ring focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2'
                )}
                title={user.username}
            >
                <span class="text-sm font-semibold">{initial}</span>
            </button>
        {/snippet}
    </Popover.Trigger>

    <Popover.Content class="w-64" align="end">
        <div class="space-y-3">
            <div class="flex items-center gap-3">
                <div
                    class="bg-primary text-primary-foreground flex size-12 items-center justify-center rounded-full"
                >
                    <span class="text-base font-semibold">{initial}</span>
                </div>
                <div class="flex-1 space-y-1">
                    <p class="text-sm font-medium leading-none">Signed in as</p>
                    <p class="text-muted-foreground text-sm">{user.username}</p>
                </div>
            </div>

            <div>
                <Button variant="outline" class="w-full justify-start gap-2" onclick={logout}>
                    <LogOut class="size-4" />
                    <span>Sign out</span>
                </Button>
            </div>
        </div>
    </Popover.Content>
</Popover.Root>
