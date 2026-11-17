#!/usr/bin/env node
/**
 * Copyright (c) Microsoft Corporation.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * The same file is in microsoft/playwright (utils/docker/check_layers.js) and in
 * the language ports. Keep the copies the same.
 */

const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync, spawnSync } = require('child_process');

const SCRIPT_NAME = path.basename(__filename);

// A file that a later layer deletes is still in the layer that created it, and
// everyone who pulls the image can read it there. So the check reads every layer,
// not the file system of the final image.
//
// Each pattern is matched against the path of a file in a layer, for example
// "root/.npm/_logs/2026-01-01-debug-0.log".
const FORBIDDEN = [
  // npm and yarn: the cache index and the debug logs record download URLs,
  // including signed URLs of a private registry.
  /(^|\/)\.npm\//,
  /(^|\/)_cacache\//,
  /(^|\/)_logs\/.*-debug-\d+\.log$/,
  /(^|\/)\.yarn\//,
  /(^|\/)\.cache\/yarn\//,
  // pip: the HTTP cache of the package index.
  /(^|\/)\.cache\/pip\//,
  // Maven and Gradle: settings.xml and gradle.properties can have credentials of
  // a repository, and the local repository records where each artifact came from.
  /(^|\/)\.m2\//,
  /(^|\/)\.gradle\//,
  // .NET and NuGet: the config can have credentials of a feed.
  /(^|\/)\.dotnet\//,
  /(^|\/)\.nuget\//,
  /(^|\/)\.local\/share\/NuGet\//,
  // Registry and package manager credentials.
  /(^|\/)\.npmrc$/,
  /(^|\/)\.yarnrc(\.yml)?$/,
  /(^|\/)\.pypirc$/,
  /(^|\/)pip\.conf$/,
  /(^|\/)\.netrc$/,
  // Source control.
  /(^|\/)\.git\//,
  /(^|\/)\.git-credentials$/,
  // Cloud, container and ssh credentials.
  /(^|\/)\.ssh\//,
  /(^|\/)\.aws\//,
  /(^|\/)\.azure\//,
  /(^|\/)\.kube\//,
  /(^|\/)\.docker\//,
  /(^|\/)\.config\/gcloud\//,
  // Private keys and key stores. Certificates (.pem, .crt) are public, and the
  // image needs the CA certificates, so they are not in this list.
  /\.key$/,
  /\.(p12|pfx|jks|keystore)$/,
  /(^|\/)id_(rsa|dsa|ecdsa|ed25519)$/,
  // Local environment files.
  /(^|\/)\.env(\.[^/]*)?$/,
];

// Files that match a pattern above, but are a part of a package and hold no secret.
const ALLOWED = [
  // The npm package has its own .npmrc with settings for npm development.
  /(^|\/)node_modules\/npm\/\.npmrc$/,
];

function usage() {
  return `usage: ${SCRIPT_NAME} [--list-files] [--base-image=<image>] playwright:localbuild-noble

Check that no layer of the docker image contains files that can hold
tokens or credentials, such as the npm cache, .npmrc, a .git directory or a private key.

  --list-files          also print every file that the layers of our Dockerfile add.
                        Layers of the base image are not listed.
  --base-image=<image>  the image in the FROM line of the Dockerfile. The check then
                        skips its layers: we cannot change them. Use it when the base
                        image has files that the check forbids, as the .NET SDK image
                        does. Without it, the check reads all layers.
`;
}

const args = process.argv.slice(2);
if (!args.length || args.includes('--help') || args.includes('-h')) {
  console.log(usage());
  process.exit(args.length ? 0 : 1);
}
const listFiles = args.includes('--list-files');
const baseImageArg = args.find(arg => arg.startsWith('--base-image='));
const baseImage = baseImageArg ? baseImageArg.substring('--base-image='.length) : undefined;
const images = args.filter(arg => arg !== '--list-files' && arg !== baseImageArg);
if (images.length !== 1 || images[0].startsWith('-')) {
  console.error(usage());
  process.exit(1);
}
const image = images[0];

const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'check-layers-'));
process.on('exit', () => fs.rmSync(tmpDir, { recursive: true, force: true }));

console.log(`Checking the layers of ${image} for files that can hold credentials...`);
// Unpack the image without a copy of the archive on disk. With pipefail, a
// failure of "docker save" fails the command too.
const saved = spawnSync('bash', ['-o', 'pipefail', '-c', 'docker save "$0" | tar -x -C "$1"', image, tmpDir], { stdio: 'inherit' });
if (saved.status !== 0) {
  console.error(`ERROR: cannot save and unpack ${image}`);
  process.exit(1);
}

let failed = false;
const layers = readLayers(tmpDir);
if (!layers.length) {
  console.error(`ERROR: found no layers in ${image}`);
  process.exit(1);
}
const baseLayerCount = baseImage ? countBaseLayers(baseImage, layers) : 0;
layers.forEach((layer, index) => {
  if (index < baseLayerCount)
    return;
  const layerFile = path.join(tmpDir, layer.file);
  const files = listLayerFiles(layerFile);
  if (listFiles && (baseImage || layer.ours)) {
    console.log(`\n=== layer ${index + 1}: ${layer.step}`);
    console.log(`=== ${files.length} file(s). A ".wh." name marks a file that the layer deletes.`);
    console.log(files.join('\n'));
  }
  const matches = withoutEmptyFiles(layerFile, files.filter(file => FORBIDDEN.some(re => re.test(file)) && !ALLOWED.some(re => re.test(file))));
  if (!matches.length)
    return;
  failed = true;
  console.log(`\nERROR: layer ${index + 1} contains ${matches.length} forbidden file(s).`);
  console.log(`  step: ${layer.step}`);
  for (const file of matches.slice(0, 20))
    console.log(`  ${file}`);
});

if (failed) {
  console.error('\nThese files stay in the image even when a later layer deletes them.');
  console.error('Do not create them, or delete them in the RUN step that creates them.');
  process.exit(1);
}
console.log(`\nChecked ${layers.length - baseLayerCount} layer(s), found no forbidden files.` + (baseLayerCount ? ` Skipped ${baseLayerCount} layer(s) of ${baseImage}.` : ''));

/**
 * Returns the layers of an unpacked "docker save" archive, bottom layer first.
 * @returns {{ file: string, diffId: string, platform: string, ours: boolean, step: string }[]}
 */
function readLayers(dir) {
  const manifest = JSON.parse(fs.readFileSync(path.join(dir, 'manifest.json'), 'utf8'))[0];
  const config = JSON.parse(fs.readFileSync(path.join(dir, manifest.Config), 'utf8'));
  // The history also has the steps that make no layer, such as ENV and ARG.
  const steps = (config.history || []).filter(step => !step.empty_layer);
  return manifest.Layers.map((file, i) => {
    const step = steps[i] || {};
    // BuildKit puts the build arguments in front of a RUN command. Remove them.
    const command = (step.created_by || '?').replace(/^RUN \|\d+ .*? \/bin\/sh -c /, 'RUN ').replace(/\s+/g, ' ');
    return {
      file,
      diffId: config.rootfs.diff_ids[i],
      platform: `${config.os}/${config.architecture}`,
      // BuildKit marks the steps of the Dockerfile that it runs. The base image has no mark.
      ours: (step.comment || '').includes('buildkit.dockerfile'),
      step: command.length > 100 ? command.slice(0, 100) + '...' : command,
    };
  });
}

/**
 * Returns the paths of the files in a layer. tar reads both plain and compressed layers.
 */
function listLayerFiles(layerFile) {
  const output = execFileSync('tar', ['-tf', layerFile], { encoding: 'utf8', maxBuffer: 1024 * 1024 * 1024 });
  return output.split('\n')
      // Paths in a layer can start with "./".
      .map(line => line.replace(/^\.\//, ''))
      // Skip directory entries: an empty directory, such as the ~/.ssh that a
      // package creates, holds no secret.
      .filter(line => line && !line.endsWith('/'));
}

/**
 * Returns the number of layers that the image has from its base image.
 */
function countBaseLayers(baseImage, layers) {
  // Pull the base image, to compare with the same version that the build used.
  // An image that exists only on this machine cannot be pulled. Use it as it is.
  spawnSync('docker', ['pull', '--quiet', '--platform', layers[0].platform, baseImage], { stdio: 'ignore' });
  const inspected = spawnSync('docker', ['image', 'inspect', '--format', '{{json .RootFS.Layers}}', baseImage], { encoding: 'utf8' });
  if (inspected.status !== 0) {
    console.error(`ERROR: cannot find the base image ${baseImage}`);
    process.exit(1);
  }
  const baseDiffIds = JSON.parse(inspected.stdout);
  if (baseDiffIds.length >= layers.length || baseDiffIds.some((diffId, i) => diffId !== layers[i].diffId)) {
    console.error(`ERROR: the layers of ${baseImage} are not the first layers of ${image}`);
    process.exit(1);
  }
  return baseDiffIds.length;
}

/**
 * Removes the empty files from the list. An empty file holds no secret, and BuildKit
 * can leave one at the target of a secret mount, for example /root/.npmrc.
 */
function withoutEmptyFiles(layerFile, files) {
  // Each call of tar reads the layer again. A layer with many forbidden files fails
  // the check with or without the empty ones.
  if (files.length > 20)
    return files;
  return files.filter(file => execFileSync('tar', ['-xOf', layerFile, file], { maxBuffer: 1024 * 1024 * 1024 }).length > 0);
}
