<script lang="ts">
    import { useLogout } from './useLogout';

    const { logout } = useLogout();
</script>

<div data-testid="logout-hook-test">
    <button data-testid="logout-button" onclick={() => logout()}> Logout </button>
</div>
