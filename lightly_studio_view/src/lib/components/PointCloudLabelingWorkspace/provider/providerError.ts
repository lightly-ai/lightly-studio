export class ProviderError extends Error {
    constructor(
        readonly code: 'auth' | 'range' | 'source' | 'schema' | 'fields' | 'corrupt' | 'limit',
        message: string,
        /**
         * The underlying failure, when `message` is a generic stand-in for it. Kept for logs
         * and diagnostics; never shown to a user in place of `message`.
         */
        readonly detail?: string
    ) {
        super(message);
        this.name = 'ProviderError';
    }
}
