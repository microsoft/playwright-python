#!/usr/bin/env node
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

const fs = require('fs');

(async () => {
  const content = fs.readFileSync(process.argv[2]).toString();
  const lines = content.split('\n');
  for (let line of lines) {
    if (line.trim().startsWith('describe')) {
      console.log('# DESCRIBE ' + line)
      continue;
    }
    if (line.trim() === '});') {
      console.log('');
      continue;
    }

    line = line.replace(/isWindows/g, 'is_win');
    line = line.replace(/isLinux/g, 'is_linux');
    line = line.replace(/isMac/g, 'is_mac');
    line = line.replace(/isWebKit/g, 'is_webkit');
    line = line.replace(/isChromium/g, 'is_chromium');
    line = line.replace(/isFirefox/g, 'is_firefox');

    let match = line.match(/it.*\(\'([^']+)\'.*async(?: function)?\s*\(\s*{(.*)}\s*\).*/);
    if (match) {
      console.log(`async def test_${match[1].replace(/[- =]|\[|\]|\>|\</g, '_')}(${match[2].trim()}):`);
      continue;
    }

    line = line.replace(/;$/g, '');
    line = line.replace(/ const /g, ' ');
    line = line.replace(/ let /g, ' ');
    line = line.replace(/\&\&/g, 'and');
    line = line.replace(/\|\|/g, 'or');
    line = line.replace(/'/g, '"');
    line = line.replace(/ = null/g, ' = None');
    line = line.replace(/===/g, '==');
    line = line.replace('await Promise.all([', 'await asyncio.gather(');
    line = line.replace(/\.\$\(/, '.query_selector(');
    line = line.replace(/\.\$$\(/, '.query_selector_all(');
    line = line.replace(/\.\$eval\(/, '.eval_on_selector(');
    line = line.replace(/\.\$$eval\(/, '.eval_on_selector_all(');

    match = line.match(/(\s+)expect\((.*)\).toEqual\((.*)\)/)
    if (match)
      line = `${match[1]}assert ${match[2]} == ${match[3]}`;
    match = line.match(/(\s+)expect\((.*)\).toBe\((.*)\)/)
      if (match)
        line = `${match[1]}assert ${match[2]} == ${match[3]}`;
    match = line.match(/(\s+)expect\((.*)\).toBeTruthy\((.*)\)/)
    if (match)
      line = `${match[1]}assert ${match[2]}`;
    match = line.match(/(\s+)expect\((.*)\).toBeGreaterThan\((.*)\)/)
    if (match)
      line = `${match[1]}assert ${match[2]} > ${match[3]}`;

    match = line.match(/(\s+)expect\((.*)\).toBeLessThan\((.*)\)/)
    if (match)
      line = `${match[1]}assert ${match[2]} < ${match[3]}`;

    match = line.match(/(\s+)expect\((.*)\).toBeGreaterThanOrEqual\((.*)\)/)
    if (match)
      line = `${match[1]}assert ${match[2]} >= ${match[3]}`;

    match = line.match(/(\s+)expect\((.*)\).toBeLessThanOrEqual\((.*)\)/)
    if (match)
      line = `${match[1]}assert ${match[2]} <= ${match[3]}`;

    line = line.replace(/ false/g, ' False');
    line = line.replace(/ true/g, ' True');

    line = line.replace(/ == null/g, ' == None');
    if (line.trim().startsWith('assert') && line.endsWith(' == True'))
      line = line.substring(0, line.length - ' == True'.length);

    // Quote evaluate
    let index = line.indexOf('.evaluate(');
    if (index !== -1) {
      const tokens = [line.substring(0, index) + '.evaluate(\''];
      let depth = 0;
      for (let i = index + '.evaluate('.length; i < line.length; ++i) {
        if (line[i] == '(')
          ++depth;
        if (line[i] == ')')
          --depth;
        if (depth < 0) {
          tokens.push('\'' + line.substring(i));
          break;
        }
        if (depth === 0 && line[i] === ',') {
          tokens.push('\"' + line.substring(i));
          break;
        }
        tokens.push(line[i]);
      }
      console.log(tokens.join(''));
      continue;
    }

    // Name keys in the dict
    index = line.indexOf('{');
    if (index !== -1) {
      let ok = false;
      for (let i = index + 1; i < line.length; ++i) {
        if (line[i] === '}') {
          try {
            console.log(line.substring(0, index) + JSON.stringify(eval('(' + line.substring(index, i + 1) + ')')).replace(/\"/g, '\'') + line.substring(i + 1));
            ok = true;
            break;
          } catch (e) {
          }
        }
      }
      if (ok) continue;
    }

    // Single line template strings
    index = line.indexOf('`');
    if (index !== -1) {
      const tokens = [line.substring(0, index) + '\''];
      let ok = false;
      for (let i = index + 1; i < line.length; ++i) {
        if (line[i] === '`') {
          tokens.push('\'' + line.substring(i + 1));
          console.log(tokens.join(''));
          ok = true;
          break;
        }
        if (line[i] === '\'')
          tokens.push('"');
        else
          tokens.push(line[i]);
      }
      if (ok) continue;
    }

    line = line.replace(/(\s+)/, '$1$1');
    if (line.endsWith('{'))
      line = line.substring(0, line.length - 1).trimEnd() + ':';
      if (line.trim().startsWith('}'))
      line = line.substring(0, line.indexOf('}')) + line.substring(line.indexOf('}') + 1).trim();
    if (line.trim().startsWith('//'))
      line = line.replace(/\/\//, '#');
    if (!line.trim())
      line = '';
    console.log(line);
  }
})();
