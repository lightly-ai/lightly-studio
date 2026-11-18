// See https://svelte.dev/docs/kit/types#app.d.ts
// for information about these interfaces
declare global {
    namespace App {
        // interface Error {}
        // interface Locals {}
        // interface PageData {}
        interface PageState {
            /** Set when a sample is opened from the dataset grid; see `datasetNavigation.ts`. */
            nav?: 'dataset';
        }
        // interface Platform {}
    }
}

export {};
