# Building the private hosted beta

The Sites source repository contains the full FarmFinder monorepo. Its publisher
expects `.openai/hosting.json` and a build command at the repository root. The
application remains in `03-app/site/`; moving it would break the canonical-data
build paths.

Install the app dependencies with `npm --prefix 03-app/site ci`, then run
`npm run build` from the repository root. The wrapper checks the root and app
hosting manifests agree, runs the existing app build and size/privacy gates,
then stages its output into the ignored root `dist/` for packaging. A failed
build does not leave a previous root artifact available for publication.

Keep both hosting manifests consistent when changing Site identity or bindings.
Do not copy canonical data, source files, credentials or private feedback into
the deployment archive: the supported packager includes the built `dist/` only.

Deployment is separate from building. Use the existing Site identity and retain
its private audience. Keep feedback flags disabled until the operations and
correction-publication gates pass. Verify the deployed home page and discovery,
map, place and profile endpoints before sharing a beta. Record the deployed
version and source commit; a merged PR or successful local build is not proof of
deployment.
