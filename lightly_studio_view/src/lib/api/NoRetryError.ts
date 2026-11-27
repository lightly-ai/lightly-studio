/** A query error that the query client does not retry. It keeps the message of its cause. */
export class NoRetryError extends Error {
    override readonly name = 'NoRetryError';

    constructor(cause: unknown) {
        super(cause instanceof Error ? cause.message : String(cause), { cause });
    }
}
