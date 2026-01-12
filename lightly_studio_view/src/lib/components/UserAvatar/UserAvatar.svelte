<script lang="ts">
    import * as Popover from '$lib/components/ui/popover';
    import { Button } from '$lib/components/ui/button';
    import { LogOut } from '@lucide/svelte';
    import { cn } from '$lib/utils/shadcn';

    interface Props {
        user: {
            username: string;
            email: string;
            role: string;
        };
    }

    let { user }: Props = $props();

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
                    'flex size-10 items-center justify-center rounded-full bg-primary text-primary-foreground transition-colors hover:bg-primary/90',
                    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2'
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
                    class="flex size-12 items-center justify-center rounded-full bg-primary text-primary-foreground"
                >
                    <span class="text-base font-semibold">{initial}</span>
                </div>
                <div class="flex-1 space-y-1">
                    <p class="text-sm font-medium leading-none">Signed in as</p>
                    <p class="text-sm text-muted-foreground">{user.username}</p>
                </div>
            </div>

            <div>
                <!-- TODO: Sign out placeholder -->
                <Button
                    variant="outline"
                    class="w-full justify-start gap-2"
                    onclick={() => {
                        console.log('Sign out');
                    }}
                >
                    <LogOut class="size-4" />
                    <span>Sign out</span>
                </Button>
            </div>
        </div>
    </Popover.Content>
</Popover.Root>
