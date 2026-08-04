# Contributing to LightlyStudio

### Welcome! We are glad that you want to contribute to our project!

We welcome contributions of all kinds, including:  
- Bug fixes  
- Documentation improvements (README, docs folder, examples)  
- New features

After you have your changes ready, and you create a new pull request, a maintainer will review your PR, may ask for changes, suggest improvements, or approve once ready.

## Requirements
- Python **3.9–3.14** (3.9 recommended)
- Uv version **0.8.17+**
- Node.js **24+** (exact version pinned in `lightly_studio_view/.nvmrc`)
- Access to **Google Cloud Platform** (request permissions from @IgorSusmelj)

## Development Quickstart

```bash
git clone git@github.com:lightly-ai/lightly_studio.git
cd lightly_studio
make download-example-dataset  # run from the repo root
cd lightly_studio              # descend into the backend subdirectory (same name as repo root)
make start
```

This will:
- Download the example dataset into `lightly_studio/datasets` (see [Clone the Repository with Test Data](#clone-the-repository-with-test-data))
- Install dependencies (uv installs Python dependencies automatically, `npm ci` the frontend ones)
- Build the frontend and the Python package
- Start an example script, which serves the app on <http://localhost:8001>

For starting it again, you can skip the build step by just calling `make start-example`.

Backend code lives in the `lightly_studio` subdirectory, frontend code in `lightly_studio_view`.
To run static checks and unit tests use the following commands

```bash
# Backend
cd lightly_studio
make static-checks
make test

# Frontend
cd lightly_studio_view
make static-checks
make test
```

When updating the code please follow our coding guidelines in [./ai_guidelines](./ai_guidelines).
AI coding tools will be able to assist.

### End-to-End Testing

We use Playwright for end-to-end testing. Tests need to be run separately for images and videos.

The e2e index scripts read the example data from `lightly_studio/datasets`, so make sure it is
present first (see [Clone the Repository with Test Data](#clone-the-repository-with-test-data)).

#### Testing with Images

First, start the e2e environment:
```bash
make -C lightly_studio start-e2e
```

Then run the tests:
```bash
cd lightly_studio_view
npm run test:e2e
```

#### Testing with Videos

First, start the e2e environment with videos:
```bash
make -C lightly_studio start-e2e-with-videos
```

Then run the video tests:
```bash
cd lightly_studio_view
npm run test:e2e-videos
```

### Documentation

Documentation is in the [docs](./lightly_studio/docs) folder. To build the documentation, move to the [docs](./lightly_studio/docs) folder and run:

```
make docs
```
This builds the documentation in the [docs/site](./lightly_studio/docs/site) folder.


Docs can be served locally with:

```
make serve
```

#### Writing Documentation

The documentation source is in [docs/docs](./lightly_studio/docs/docs). The documentation is
written in Markdown and built with MkDocs using the Material theme. For more information regarding
formatting, see:

- https://squidfunk.github.io/mkdocs-material/reference/
- https://www.mkdocs.org/user-guide/writing-your-docs/


## Development Environment Setup

See [Requirements](#requirements) above for the Python, Uv, and Node.js versions needed before
following the steps below.

### Clone the Repository with Test Data

Download the example dataset, which contains sample data used during development. Run this from
the repository root:

```bash
make download-example-dataset
```

This clones the data into `lightly_studio/datasets`, which is where the `EXAMPLES_*` paths in
`.env.example` and the e2e index scripts expect to find it.

### Define Environment Variables

Copy `.env.example` to `.env`:

```shell
cd lightly_studio
cp .env.example .env
```

Now edit the `.env` file:

* Optionally change the `EXAMPLES_*` paths to point to data on your machine. You can leave the
defaults to use the cloned dataset examples data.

### Run Examples

Choose a script in `lightly_studio/src/lightly_studio/examples` directory and run it like this:

```shell
cd lightly_studio
uv run src/lightly_studio/examples/example.py
```

### Start the Application

`make start` builds the frontend into the backend package and serves the whole application on
<http://localhost:8001>, so this single command is all that is needed:

```shell
cd lightly_studio
make start
```

### Frontend Development with Hot Reloading

Optional, for UI work only. This runs the Vite dev server in front of the backend, so keep
`make start` running in another terminal.

```shell
cd lightly_studio_view
cp .env.example .env.local
npm run dev
```

For this to work, the backend must already be serving on <http://localhost:8001> — either via
`make start` (or `make start-example`), or by running any script directly with
`uv run src/lightly_studio/examples/<script>.py` (see [Run Examples](#run-examples)). Either way,
`.env.local` needs to point at it:

```shell
PUBLIC_SAMPLES_URL=http://localhost:8001/images
PUBLIC_LIGHTLY_STUDIO_API_URL=http://localhost:8001/
```

### Exploring the Makefile

There are three Makefiles: one in `lightly_studio` for the backend, build, e2e and migration
targets, one in `lightly_studio_view` for the frontend, and one in the repository root that
delegates to both. Some commonly used commands:

Run tests:

```shell
make test
```

Format code:

```shell
make format
```

Run these from the directory you are working in, or from the root to cover both sides. You can
explore more available commands directly in the `Makefile`.

### Contributor License Agreement (CLA)

To contribute to this repository, you must sign a Contributor License Agreement (CLA).
This is a one-time process done through GitHub when you open your first pull request.
You will be prompted automatically.

By signing the CLA, you agree that your contributions may be used under the terms of the project license.
