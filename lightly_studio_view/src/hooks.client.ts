import { registerApiErrorInterceptor } from '$lib/api/registerApiErrorInterceptor';

// Registered here, not in a component, so it also covers requests from `load` functions, which
// run before the root layout.
registerApiErrorInterceptor();
