// Wraps an async function so its calls run one after another. onnxruntime-web does not
// support overlapping runs on one session, and the editor and a batch can share a session.
export const runOneAtATime = <Args extends unknown[], Result>(
    task: (...args: Args) => Promise<Result>
): ((...args: Args) => Promise<Result>) => {
    let previous: Promise<unknown> = Promise.resolve();
    return (...args) => {
        const current = previous.then(() => task(...args));
        // The next call waits for this one to end, whether it failed or not.
        previous = current.catch(() => undefined);
        return current;
    };
};
