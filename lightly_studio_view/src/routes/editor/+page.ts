import type { PageLoad } from './$types';

export const load: PageLoad = async () => {
  return {
    title: 'Monaco Editor Example',
    description: 'Interactive code editor with Monaco Editor integration'
  };
};

// Enable client-side rendering for Monaco Editor
export const ssr = false;
export const prerender = false;