<script lang="ts">
	import { goto } from '$app/navigation';
	import Button from '$lib/components/ui/button/button.svelte';
	import Input from '$lib/components/ui/input/input.svelte';
	import FormField from '$lib/components/FormField/FormField.svelte';
	import { useAuth } from '$lib/hooks/useAuth';
	import { login } from '$lib/api/lightly_studio_local/sdk.gen';
	import { toast } from 'svelte-sonner';

	const auth = useAuth();

	let email = $state('');
	let password = $state('');
	let isLoading = $state(false);
	let errorMessage = $state('');

	async function handleSubmit(event: Event) {
		event.preventDefault();

		if (!email || !password) {
			errorMessage = 'Please enter both email and password';
			return;
		}

		isLoading = true;
		errorMessage = '';

		try {
			const { data, error } = await login({
				body: {
					username: email,
					password: password
				}
			});

			if (error) {
				errorMessage = 'Invalid email or password';
				toast.error('Login failed', {
					description: 'Invalid email or password'
				});
				isLoading = false;
				return;
			}

			if (data) {
				// Store token and user info
				auth.login(data.access_token, data.user);

				// Redirect to home
				goto('/');
			}
		} catch (err) {
			console.error('Login error:', err);
			errorMessage = 'An unexpected error occurred';
			toast.error('Login failed', {
				description: 'An unexpected error occurred'
			});
		} finally {
			isLoading = false;
		}
	}
</script>

<div class="flex h-screen w-full items-center justify-center bg-background">
	<div class="w-full max-w-md space-y-6 rounded-lg border border-border bg-card p-8 shadow-lg">
		<div class="space-y-2 text-center">
			<h1 class="text-3xl font-bold">LightlyStudio</h1>
			<p class="text-muted-foreground">Sign in to continue</p>
		</div>

		<form onsubmit={handleSubmit} class="space-y-4">
			<FormField label="Email" forComponent="email">
				<Input
					id="email"
					type="email"
					placeholder="Enter your email"
					bind:value={email}
					disabled={isLoading}
					required
				/>
			</FormField>

			<FormField label="Password" forComponent="password">
				<Input
					id="password"
					type="password"
					placeholder="Enter your password"
					bind:value={password}
					disabled={isLoading}
					required
				/>
			</FormField>

			{#if errorMessage}
				<div class="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
					{errorMessage}
				</div>
			{/if}

			<Button type="submit" class="w-full" disabled={isLoading}>
				{isLoading ? 'Signing in...' : 'Sign in'}
			</Button>
		</form>

		<div class="text-center text-sm text-muted-foreground">
			<p>Default credentials: admin@localhost / admin</p>
		</div>
	</div>
</div>