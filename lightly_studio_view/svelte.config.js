import adapter from '@sveltejs/adapter-static';

export default {
    kit: {
        adapter: adapter({
            // default options are shown. On some platforms
            // these options are set automatically — see below
            pages: 'build',
            assets: 'build',
            fallback: 'index.html',
            precompress: false,
            strict: true
        })
    },
    compilerOptions: {
        // disable all warnings coming from src/lib/components/ui
        warningFilter: (warning) => !warning.filename?.includes('src/lib/components/ui')
    }
};
