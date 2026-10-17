/**
 * Copyright (c) Microsoft Corporation.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

// Port of tests/config/remote-server-impl.js. tests/helpers/remote_server.py runs it
// with the driver's Node.js. It loads playwright-core from options.playwrightPath (the
// driver package) instead of require('playwright-core').

const fs = require('fs');
const cluster = require('cluster');

async function start() {
  const { playwrightPath, browserTypeName, launchOptions, stallOnClose, disconnectOnSIGHUP, exitOnFile, exitOnWarning, startStopAndRunHttp } = JSON.parse(process.argv[2]);
  if (stallOnClose) {
    launchOptions.__testHookGracefullyClose = () => {
      console.log(`(stalled=>true)`);
      return new Promise(() => { });
    };
  }
  if (exitOnWarning)
    process.on('warning', () => process.exit(43));
  if (disconnectOnSIGHUP)
    launchOptions.handleSIGHUP = false;

  const playwright = require(playwrightPath);

  if (startStopAndRunHttp) {
    const browser = await playwright[browserTypeName].launch(launchOptions);
    await browser.close();
    console.log(`(wsEndpoint=>none)`);
    console.log(`(closed=>success)`);
    require('http').createServer(() => {}).listen();
    return;
  }

  const browserServer = await playwright[browserTypeName].launchServer(launchOptions);
  if (disconnectOnSIGHUP)
    process.on('SIGHUP', () => browserServer._disconnectForTest());

  if (exitOnFile) {
    (async function waitForFileAndExit() {
      while (true) {
        if (fs.existsSync(exitOnFile))
          break;
        await new Promise(f => setTimeout(f, 100));
      }
      process.exit(42);
    })();
  }

  browserServer.on('close', (exitCode, signal) => {
    console.log(`(exitCode=>${exitCode})`);
    console.log(`(signal=>${signal})`);
  });
  console.log(`(tempDir=>${browserServer._userDataDirForTest})`);
  console.log(`(pid=>${browserServer.process().pid})`);
  console.log(`(wsEndpoint=>${browserServer.wsEndpoint()})`);
}

process.on('uncaughtException', error => console.log(error));
process.on('unhandledRejection', reason => console.log(reason));

if (cluster.isWorker || !JSON.parse(process.argv[2]).inCluster) {
  start();
} else {
  cluster.fork();
  cluster.on('exit', (worker, code, signal) => {
    process.exit(0);
  });
}
