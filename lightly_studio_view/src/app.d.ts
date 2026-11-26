// See https://svelte.dev/docs/kit/types#app.d.ts
// for information about these interfaces
declare global {
    namespace App {
        // interface Error {}
        // interface Locals {}
        // interface PageData {}
        interface PageState {
            /** Set on the history entry that the point cloud page pushed to open a camera. */
            cameraEntry?: boolean;
        }
        // interface Platform {}
    }
}

export {};
