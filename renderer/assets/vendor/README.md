# Vendored browser libraries

`elevenlabs-client-1.36.1.js` is `@elevenlabs/client` 1.36.1 bundled into one ES
module, so the voice assistant does not depend on a CDN being reachable from a
dealer's network. `assets/voice.js` loads it only when someone presses the mic.

Rebuild (or upgrade — change the version in both places and in `voice.js`):

```bash
mkdir /tmp/elb && cd /tmp/elb && npm init -y
npm install @elevenlabs/client@1.36.1 esbuild@0.25
echo 'export { Conversation } from "@elevenlabs/client";' > entry.js
npx esbuild entry.js --bundle --format=esm --platform=browser --minify \
    --target=es2020 --outfile=elevenlabs-client-1.36.1.js
```
