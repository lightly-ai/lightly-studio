<script lang="ts">
	import { useAuth } from '$lib/hooks/useAuth';
	import * as Popover from '$lib/components/ui/popover/index.js';
	import Button from '$lib/components/ui/button/button.svelte';
	import LogOut from '@lucide/svelte/icons/log-out';
	import User from '@lucide/svelte/icons/user';
	import Key from '@lucide/svelte/icons/key';
	import { cn } from '$lib/utils';

	const auth = useAuth();
	let open = $state(false);

	const user = $derived(auth.getUser());
	const token = $derived(auth.getToken());

	// Get initials from email
	const initials = $derived.by(() => {
		if (!user?.email) return '?';
		const parts = user.email.split('@')[0];
		return parts
			.split('.')
			.map((part) => part[0])
			.join('')
			.toUpperCase()
			.slice(0, 2);
	});

	type ChildProps = {
		props: Record<string, unknown>;
	};
</script>

<Popover.Root bind:open>
	<Popover.Trigger>
		{#snippet child({ props }: ChildProps)}
			<button
				{...props}
				type="button"
				class={cn(
					'flex size-10 items-center justify-center rounded-full bg-primary text-primary-foreground transition-colors hover:bg-primary/90',
					'focus-visible:ring-ring focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2'
				)}
				title={user?.email || 'User'}
			>
				<span class="text-sm font-semibold">{initials}</span>
			</button>
		{/snippet}
	</Popover.Trigger>

	<Popover.Content class="w-80" align="end">
		<div class="space-y-4">
			<div class="flex items-center gap-3 border-b border-border pb-3">
				<div
					class="flex size-12 items-center justify-center rounded-full bg-primary text-primary-foreground"
				>
					<span class="text-base font-semibold">{initials}</span>
				</div>
				<div class="flex-1 space-y-1">
					<p class="text-sm font-medium leading-none">Signed in as</p>
					<p class="text-sm text-muted-foreground">{user?.email || 'Unknown'}</p>
				</div>
			</div>

			<div class="space-y-2">
				<div class="flex items-start gap-2">
					<User class="mt-0.5 size-4 text-muted-foreground" />
					<div class="flex-1">
						<p class="text-xs font-medium text-muted-foreground">User ID</p>
						<p class="mt-1 break-all text-xs font-mono">{user?.user_id || 'N/A'}</p>
					</div>
				</div>

				<div class="flex items-start gap-2">
					<Key class="mt-0.5 size-4 text-muted-foreground" />
					<div class="flex-1">
						<p class="text-xs font-medium text-muted-foreground">Token</p>
						<p class="mt-1 break-all text-xs font-mono">{token || 'N/A'}</p>
					</div>
				</div>
			</div>

			<div class="border-t border-border pt-3">
				<Button
					variant="outline"
					class="w-full justify-start gap-2"
					onclick={() => {
						open = false;
						auth.logout();
					}}
				>
					<LogOut class="size-4" />
					<span>Sign out</span>
				</Button>
			</div>
		</div>
	</Popover.Content>
</Popover.Root>