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

// @ts-check

// Generates the public Python API (playwright/{async,sync}_api/_generated.py)
// and its TypedDicts (playwright/_impl/_api_structures.py) from the upstream
// Playwright docs (docs/src/api in microsoft/playwright).
//
// Usage:
//   PW_SRC_DIR=<microsoft/playwright checkout> node scripts/codegen/generate_api.js --flavor async|sync|structs [--out <file>]
//
// The docs are parsed with the upstream parser (utils/doclint/api_parser.js) and
// filtered for Python. Facts that the docs do not contain come from
// python_rules.js. The output is not formatted; run isort and black on it.

'use strict';

const fs = require('fs');
const path = require('path');
const rules = require('./python_rules');

/**
 * @typedef {{
 *   kind: 'name' | 'class' | 'struct' | 'union' | 'list' | 'dict' | 'callable' | 'literal' | 'pattern' | 'awaitable' | 'ecm' | 'cm',
 *   name?: string,
 *   wrapper?: boolean,
 *   members?: PyType[],
 *   item?: PyType,
 *   key?: PyType,
 *   value?: PyType,
 *   args?: PyType[] | null,
 *   ret?: PyType,
 *   values?: string[],
 *   inner?: PyType | null,
 *   docType?: any,
 *   place?: string,
 *   dir?: 'in' | 'out',
 * }} PyType
 */

/**
 * @typedef {{
 *   name: string,
 *   implName: string,
 *   type: PyType,
 *   optional: boolean,
 *   comment: string,
 *   deprecated: string | undefined,
 *   documented: boolean,
 * }} PyParam
 */

/**
 * @typedef {{
 *   kind: 'property' | 'method',
 *   name: string,
 *   isAsync: boolean,
 *   positional: PyParam[],
 *   keywordOnly: PyParam[],
 *   returnType: PyType | null,
 *   comment: string | null,
 *   documented: boolean,
 * }} PyMember
 */

/**
 * @typedef {{
 *   name: string,
 *   base: string,
 *   events: any[],
 *   members: PyMember[],
 * }} PyClass
 */

// ---------------------------------------------------------------------------
// Command line and upstream modules.

function parseArgs(argv) {
  const result = { flavor: 'async', out: '' };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--flavor')
      result.flavor = argv[++i];
    else if (argv[i] === '--out')
      result.out = argv[++i];
    else
      fail(`Unknown argument: ${argv[i]}`);
  }
  if (!['async', 'sync', 'structs'].includes(result.flavor))
    fail(`--flavor must be "async", "sync" or "structs", got "${result.flavor}"`);
  return result;
}

/** @param {string} message */
function fail(message) {
  console.error(message);
  process.exit(1);
}

const options = parseArgs(process.argv.slice(2));
const isAsync = options.flavor === 'async';

const PW_SRC_DIR = process.env.PW_SRC_DIR;
if (!PW_SRC_DIR)
  fail('Set PW_SRC_DIR to a microsoft/playwright checkout at the release branch in DRIVER_VERSION.');
const { parseApi } = require(path.join(PW_SRC_DIR, 'utils', 'doclint', 'api_parser'));
const { Type, parseCodeLang } = require(path.join(PW_SRC_DIR, 'utils', 'doclint', 'documentation'));
const md = require(path.join(PW_SRC_DIR, 'utils', 'markdown'));

const BASE_CLASS = isAsync ? 'AsyncBase' : 'SyncBase';
const CONTEXT_MANAGER_CLASS = isAsync ? 'AsyncContextManager' : 'SyncContextManager';
const EVENT_CONTEXT_MANAGER_CLASS = isAsync ? 'AsyncEventContextManager' : 'EventContextManager';

/** @type {string[]} */
const errors = [];
/** @type {Set<string>} */
const usedRules = new Set();
/** @type {Set<string>} */
const usedStructs = new Set();
/** @type {Map<string, PyType[]>} every use of each struct name */
const structUses = new Map();

// ---------------------------------------------------------------------------
// Names.

/**
 * Compares by name, in code point order (as Python's sorted()). The generated
 * files list classes, members, keyword-only parameters, events and
 * TypedDicts in this order.
 * @param {string} a
 * @param {string} b
 */
function byName(a, b) {
  return a < b ? -1 : a > b ? 1 : 0;
}

/** @param {string} name */
function toSnakeCase(name) {
  // Same as playwright._impl._helper.to_snake_case.
  return name.replace(/((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))/g, '_$1').toLowerCase();
}

/**
 * Looks up a rule and records that it was used.
 * @param {string} table
 * @param {string} key
 */
function lookupRule(table, key) {
  const entries = /** @type {any} */ (rules)[table];
  if (Object.prototype.hasOwnProperty.call(entries, key)) {
    usedRules.add(`${table}:${key}`);
    return entries[key];
  }
  for (const pattern of Object.keys(entries)) {
    if (!pattern.includes('*'))
      continue;
    const regex = new RegExp('^' + pattern.split('*').map(escapeRegExp).join('[^.]+') + '$');
    if (regex.test(key)) {
      usedRules.add(`${table}:${pattern}`);
      return entries[pattern];
    }
  }
  return undefined;
}

/** @param {string} text */
function escapeRegExp(text) {
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// ---------------------------------------------------------------------------
// Docs.

function loadDocumentation() {
  const documentation = parseApi(path.join(PW_SRC_DIR, 'docs', 'src', 'api'));
  documentation.filterForLanguage('python');
  return documentation;
}

const documentation = loadDocumentation();

/** @type {Set<string>} */
const generatedClassNames = new Set(documentation.classesArray
    .map(c => c.name)
    .filter(name => !rules.handWrittenClasses.includes(name)));

/** @param {any} member */
function isPythonProperty(member) {
  if (member.kind === 'property')
    return true;
  if (member.kind !== 'method' || member.async || member.argsArray.length)
    return false;
  const name = toSnakeCase(member.alias);
  return !name.startsWith('is_') && !name.startsWith('as_') && name !== 'connect_to_server';
}

/** @param {any} member */
function memberLink(member) {
  const variable = toSnakeCase(member.clazz.varName);
  if (member.kind === 'event')
    return '`' + `${variable}.on('${member.alias.toLowerCase()}')` + '`';
  if (isPythonProperty(member))
    return '`' + `${variable}.${toSnakeCase(member.alias)}` + '`';
  return '`' + `${variable}.${toSnakeCase(member.alias)}()` + '`';
}

documentation.setLinkRenderer(({ clazz, member, param, option }) => {
  if (param)
    return '`' + toSnakeCase(param.alias) + '`';
  if (option)
    return '`' + option.alias.split('.').map(toSnakeCase).join('.') + '`';
  if (member)
    return memberLink(member);
  if (clazz)
    return '`' + clazz.name + '`';
  return undefined;
});

// ---------------------------------------------------------------------------
// Docstrings.

const KEPT_CODE_LANGUAGES = new Set(['html', 'yml', 'sh', 'py', 'python']);

/** @param {any[]} nodes */
function filterCodeBlocks(nodes) {
  const result = [];
  for (const node of nodes) {
    if (node.type === 'code' && node.codeLang) {
      if (node.codeLang === 'python async' || node.codeLang === 'python sync') {
        if (node.codeLang !== `python ${options.flavor}`)
          continue;
      } else if (!KEPT_CODE_LANGUAGES.has(parseCodeLang(node.codeLang).highlighter)) {
        continue;
      }
    }
    if (node.children)
      node.children = filterCodeBlocks(node.children);
    result.push(node);
  }
  return result;
}

/**
 * Renders a member or argument description as plain text. Same as the
 * upstream generateSourceCodeComment(), but keeps only the code examples for
 * Python and for this flavor.
 * @param {any[] | undefined} spec
 */
function renderSpec(spec) {
  const nodes = filterCodeBlocks((spec || [])
      .filter(n => !n.type.startsWith('h') && (n.type !== 'li' || n.liType !== 'default'))
      .map(n => md.clone(n)));
  md.visitAll(nodes, node => {
    if (node.type === 'li' && node.liType === 'bullet')
      node.liType = 'default';
    if (node.type === 'code' && node.codeLang)
      node.codeLang = parseCodeLang(node.codeLang).highlighter;
  });
  return md.render(nodes, { maxColumns: 120 - 5, omitLastCR: true, flattenText: true, noteMode: 'compact' });
}

/** @param {string} text */
function escapeDocstring(text) {
  return escapeBackslashes(text).replace(/"/g, '\\"');
}

/**
 * Parameter descriptions keep their quotes: they never end the docstring.
 * @param {string} text
 */
function escapeBackslashes(text) {
  return text.replace(/\\/g, '\\\\');
}

/**
 * @param {string} text
 * @param {string} indent
 */
function indentParagraph(text, indent) {
  const lines = text.split('\n');
  return [lines[0], ...lines.slice(1).map(line => indent + line)].join('\n');
}

/** @param {string} text */
function resolveRelativeLinks(text) {
  return text.replace(/\[([^\]]+)\]\((\.[^)]+)\)/g, (match, linkText, href) => {
    const resolved = new URL(href.replace(/\.md/g, ''), 'https://playwright.dev/python/docs/api/').href;
    return `[${linkText}](${resolved})`;
  });
}

/**
 * Member description: one blank line between paragraphs, indented.
 * @param {string} text
 * @param {string} indent
 */
function formatComment(text, indent) {
  const result = [];
  let lastWasBlank = true;
  for (const line of escapeDocstring(text).split('\n')) {
    if (!line.trim()) {
      lastWasBlank = true;
      continue;
    }
    if (lastWasBlank) {
      lastWasBlank = false;
      result.push('');
    }
    result.push(line);
  }
  return resolveRelativeLinks(indentParagraph(result.join('\n'), indent));
}

// ---------------------------------------------------------------------------
// Types.

/** @param {string} name */
const NAME = name => /** @type {PyType} */ ({ kind: 'name', name });
const ANY = NAME('Any');
const NONE = NAME('None');

/** @param {PyType} t */
const isNone = t => t.kind === 'name' && t.name === 'None';

/** @param {string} name */
function isStringLiteral(name) {
  return name.startsWith('"') && name.endsWith('"');
}

/**
 * @param {PyType[]} members
 * @returns {PyType}
 */
function makeUnion(members) {
  /** @type {PyType[]} */
  const flat = [];
  for (const member of members) {
    if (member.kind === 'union')
      flat.push(...(member.members || []));
    else
      flat.push(member);
  }
  /** @type {PyType[]} */
  const result = [];
  /** @type {PyType | null} */
  let literal = null;
  const seen = new Set();
  for (const member of flat) {
    if (member.kind === 'literal') {
      if (!literal) {
        literal = { kind: 'literal', values: [] };
        result.push(literal);
      }
      for (const value of member.values || []) {
        if (!(literal.values || []).includes(value))
          literal.values?.push(value);
      }
      continue;
    }
    const key = annotation(member, false);
    if (seen.has(key))
      continue;
    seen.add(key);
    result.push(member);
  }
  if (literal)
    literal.values?.sort();
  return result.length === 1 ? result[0] : { kind: 'union', members: result };
}

/**
 * @param {any} type docs Type
 * @param {{ dir: 'in' | 'out', place: string, fnReturn?: boolean }} ctx
 * @returns {PyType}
 */
function toPy(type, ctx) {
  if (type.union)
    return makeUnion(type.union.map(t => toPy(t, ctx)));
  const name = type.name;
  if (isStringLiteral(name))
    return { kind: 'literal', values: [name.substring(1, name.length - 1)] };
  switch (name) {
    case 'string':
    case 'URL':
      return NAME('str');
    case 'boolean':
      return NAME('bool');
    case 'int':
    case 'long':
      return NAME('int');
    case 'float':
      return NAME('float');
    case 'null':
    case 'void':
    case 'undefined':
      return NONE;
    case 'any':
    case 'unknown':
    case 'Serializable':
    case 'EvaluationArgument':
      return ANY;
    case 'Buffer':
    case 'ReadStream':
      return NAME('bytes');
    case 'Date':
      return NAME('datetime.datetime');
    case 'RegExp':
      return { kind: 'pattern' };
    case 'path':
      return ctx.dir === 'in' ? makeUnion([NAME('str'), NAME('pathlib.Path')]) : NAME('pathlib.Path');
    case 'function': {
      if (!type.args)
        return { kind: 'callable', args: null, ret: ANY };
      const args = type.args.map(t => toPy(t, { ...ctx, fnReturn: false }));
      const ret = type.returnType ? toPy(type.returnType, { ...ctx, fnReturn: true }) : ANY;
      return { kind: 'callable', args, ret };
    }
    case 'Promise': {
      const inner = type.templates ? toPy(type.templates[0], { ...ctx, fnReturn: false }) : ANY;
      // A callback may return a promise: in Python, the async API accepts an
      // awaitable there; the sync API does not.
      if (ctx.fnReturn && isAsync && !(inner.kind === 'name' && inner.name === 'Any'))
        return { kind: 'awaitable', inner };
      return inner;
    }
    case 'Array':
      return { kind: 'list', item: toPy(type.templates[0], ctx), dir: ctx.dir };
    case 'Object':
    case 'Map':
      if (type.templates)
        return { kind: 'dict', key: toPy(type.templates[0], ctx), value: toPy(type.templates[1], ctx) };
      if (type.properties && type.properties.length)
        return { kind: 'struct', docType: type, place: ctx.place, dir: ctx.dir };
      return { kind: 'dict', key: undefined, value: undefined };
    case 'EventContextManager':
      return { kind: 'ecm', inner: type.templates ? toPy(type.templates[0], ctx) : null };
    case 'Disposable':
      return { kind: 'cm' };
    case 'Error':
    case 'FormData':
      return { kind: 'class', name, wrapper: false };
  }
  if (generatedClassNames.has(name))
    return { kind: 'class', name, wrapper: true };
  throw new Error(`Unknown docs type "${name}" at ${ctx.place}`);
}

/** @param {PyType} t */
function structName(t) {
  const place = /** @type {string} */ (t.place);
  const name = t.docType.langAliases?.python || t.docType.langAliases?.default;
  if (!name) {
    errors.push(`No Python name for the struct at ${place}: {${t.docType.properties.map(p => p.name).join(', ')}}`);
    return 'typing.Dict';
  }
  usedStructs.add(name);
  const uses = structUses.get(name) || [];
  if (!uses.some(use => use.place === t.place && use.dir === t.dir))
    uses.push(t);
  structUses.set(name, uses);
  return name;
}

/**
 * Python annotation text.
 * @param {PyType} t
 * @param {boolean=} record whether to record used struct names
 * @returns {string}
 */
function annotation(t, record = true) {
  switch (t.kind) {
    case 'name':
      return t.name === 'Any' ? 'typing.Any' : /** @type {string} */ (t.name);
    case 'class':
      return `"${t.name}"`;
    case 'struct':
      return record ? structName(t) : `struct:${t.place}`;
    case 'union': {
      const members = t.members || [];
      const others = members.filter(m => !isNone(m)).map(m => annotation(m, record));
      const inner = others.length === 1 ? others[0] : `typing.Union[${others.join(', ')}]`;
      return members.some(isNone) ? `typing.Optional[${inner}]` : inner;
    }
    case 'list':
      return `typing.${t.dir === 'in' ? 'Sequence' : 'List'}[${annotation(/** @type {PyType} */ (t.item), record)}]`;
    case 'dict':
      if (!t.key)
        return 'typing.Dict';
      return `typing.Dict[${annotation(t.key, record)}, ${annotation(/** @type {PyType} */ (t.value), record)}]`;
    case 'callable':
      if (!t.args)
        return 'typing.Callable';
      return `typing.Callable[[${t.args.map(a => annotation(a, record)).join(', ')}], ${annotation(/** @type {PyType} */ (t.ret), record)}]`;
    case 'literal':
      return `Literal[${(t.values || []).map(v => JSON.stringify(v)).join(', ')}]`;
    case 'pattern':
      return 'typing.Pattern[str]';
    case 'awaitable':
      return `typing.Awaitable[${annotation(/** @type {PyType} */ (t.inner), record)}]`;
    case 'ecm':
      return t.inner ? `${EVENT_CONTEXT_MANAGER_CLASS}[${annotation(t.inner, record)}]` : EVENT_CONTEXT_MANAGER_CLASS;
    case 'cm':
      return `"${CONTEXT_MANAGER_CLASS}"`;
  }
  throw new Error(`Unknown type kind ${t.kind}`);
}

/** @param {string} text */
function makeOptional(text) {
  if (text.startsWith('Union[')) {
    if (text.endsWith('None]'))
      return text;
    return text.substring(0, text.length - 1) + ', None]';
  }
  return `Union[${text}, None]`;
}

/** @param {string[]} items */
function sortDocUnion(items) {
  const key = item => item === 'None' ? '}' : item;
  return [...items].sort((a, b) => key(a) < key(b) ? -1 : key(a) > key(b) ? 1 : 0);
}

/**
 * Type text for docstrings. Same format as the old generator: structs are
 * expanded, unions are sorted with None last.
 * @param {PyType} t
 * @returns {string}
 */
function docType(t) {
  switch (t.kind) {
    case 'name':
      return /** @type {string} */ (t.name);
    case 'class':
      return /** @type {string} */ (t.name);
    case 'struct': {
      const fields = t.docType.properties.map(p => {
        const field = docType(toPy(p.type, { dir: t.dir || 'out', place: `${t.place}.${p.name}` }));
        return `${p.name}: ${p.required ? field : makeOptional(field)}`;
      });
      return `{${fields.join(', ')}}`;
    }
    case 'union': {
      const members = t.members || [];
      if (members.length === 2 && members.some(isNone))
        return makeOptional(docType(/** @type {PyType} */ (members.find(m => !isNone(m)))));
      const items = [];
      for (const member of members) {
        if (member.kind === 'literal')
          items.push(...(member.values || []).map(v => `"${v}"`));
        else
          items.push(docType(member));
      }
      return `Union[${sortDocUnion(items).join(', ')}]`;
    }
    case 'list':
      return `${t.dir === 'in' ? 'Sequence' : 'List'}[${docType(/** @type {PyType} */ (t.item))}]`;
    case 'dict':
      if (!t.key)
        return 'Dict';
      return `Dict[${docType(t.key)}, ${docType(/** @type {PyType} */ (t.value))}]`;
    case 'callable':
      if (!t.args)
        return 'Callable';
      return `Callable[[${t.args.map(docType).join(', ')}], ${docType(/** @type {PyType} */ (t.ret))}]`;
    case 'literal': {
      const values = (t.values || []).map(v => `"${v}"`);
      return values.length === 1 ? values[0] : `Union[${values.join(', ')}]`;
    }
    case 'pattern':
      return 'Pattern[str]';
    case 'awaitable':
      return `typing.Awaitable[${docType(/** @type {PyType} */ (t.inner))}]`;
    case 'ecm':
      return t.inner ? `EventContextManager[${docType(t.inner)}]` : 'EventContextManager';
    case 'cm':
      return CONTEXT_MANAGER_CLASS;
  }
  throw new Error(`Unknown type kind ${t.kind}`);
}

/**
 * Visits the type, but not the fields of structs: a struct crosses into the
 * implementation as a plain dict, whatever its fields are.
 * @param {PyType} t
 * @param {(t: PyType) => boolean} predicate
 * @returns {boolean}
 */
function someType(t, predicate) {
  if (predicate(t))
    return true;
  const children = [
    ...(t.members || []),
    ...(t.args || []),
    t.item, t.key, t.value, t.ret, t.inner,
  ].filter(Boolean);
  return children.some(c => someType(/** @type {PyType} */ (c), predicate));
}

/**
 * The Python expression that passes a parameter to the implementation.
 * @param {PyParam} param
 */
function forwardExpression(param) {
  const t = param.type;
  const name = param.name;
  if (someType(t, c => c.kind === 'callable'))
    return `self._wrap_handler(${name})`;
  if (param.implName === 'timeout' && someType(t, c => c.kind === 'name' && c.name === 'float'))
    return `to_milliseconds(${name})`;
  if (someType(t, c =>
    (c.kind === 'name' && c.name === 'Any') ||
    c.kind === 'dict' ||
    (c.kind === 'list' && c.dir === 'in') ||
    (c.kind === 'class' && !!c.name && c.name.includes('Handle'))))
    return `mapping.to_impl(${name})`;
  if (t.kind === 'class' && t.wrapper)
    return param.optional ? `${name}._impl_obj if ${name} else None` : `${name}._impl_obj`;
  if (t.kind === 'union' && t.members?.length === 2 && t.members.some(isNone)) {
    const other = /** @type {PyType} */ (t.members.find(m => !isNone(m)));
    if (other.kind === 'class' && other.wrapper)
      return `${name}._impl_obj if ${name} else None`;
  }
  // A union such as `str | Locator`: unwrap whichever value was passed.
  if (someType(t, c => c.kind === 'class' && !!c.wrapper))
    return `mapping.to_impl(${name})`;
  return name;
}

/**
 * The function that converts a return value from the implementation.
 * @param {PyType | null} t
 */
function returnWrapper(t) {
  if (!t || !someType(t, c => c.kind === 'class' || c.kind === 'struct' || c.kind === 'cm'))
    return 'mapping.from_maybe_impl';
  if (t.kind === 'union' && t.members?.length === 2 && t.members.some(isNone))
    return 'mapping.from_impl_nullable';
  if (t.kind === 'list')
    return 'mapping.from_impl_list';
  if (t.kind === 'dict')
    return 'mapping.from_impl_dict';
  return 'mapping.from_impl';
}

// ---------------------------------------------------------------------------
// Python model.

/**
 * @param {any} clazz
 * @param {any} member
 * @returns {PyMember}
 */
function buildMember(clazz, member) {
  const memberPlace = `${clazz.name}.${member.name}`;
  const returnType = member.type.name === 'void' && !member.type.union ? null : toPy(member.type, { dir: 'out', place: memberPlace });
  const isEventContextManager = returnType?.kind === 'ecm';

  /** @type {{ arg: any, isOption: boolean }[]} */
  const args = [];
  for (const arg of member.argsArray) {
    if (arg.name === 'options') {
      for (const option of arg.type.properties)
        args.push({ arg: option, isOption: true });
    } else {
      args.push({ arg, isOption: false });
    }
  }

  /** @param {{ arg: any, isOption: boolean }} entry */
  const toParam = ({ arg, isOption }) => {
    const place = `${memberPlace}.${arg.name}`;
    const type = toPy(arg.type, { dir: 'in', place });
    const nullable = type.kind === 'union' && !!type.members?.some(isNone);
    return /** @type {PyParam} */ ({
      name: toSnakeCase(arg.alias),
      implName: arg.name,
      type,
      optional: isOption || !arg.required || nullable,
      comment: renderSpec(arg.spec),
      deprecated: arg.deprecated,
      documented: true,
    });
  };

  /** @param {{ arg: any, isOption: boolean }} entry */
  const isPositional = ({ arg, isOption }) => !isOption || rules.positionalOptions.includes(arg.name);
  /** @type {PyParam[]} */
  const positional = args.filter(isPositional).map(toParam);
  /** @type {PyParam[]} */
  const keywordOnly = args.filter(a => !isPositional(a)).map(toParam);
  for (const extra of lookupRule('extraOptions', memberPlace) || []) {
    keywordOnly.push({
      name: toSnakeCase(extra.name),
      implName: extra.name,
      type: toPy(Type.parse(extra.type), { dir: 'in', place: `${memberPlace}.${extra.name}` }),
      optional: true,
      comment: '',
      deprecated: undefined,
      documented: false,
    });
  }
  keywordOnly.sort((a, b) => byName(a.name, b.name));
  let sawOptional = false;
  for (const param of positional) {
    if (sawOptional && !param.optional)
      errors.push(`${memberPlace}: required parameter ${param.name} follows an optional one; fix the docs`);
    sawOptional = sawOptional || param.optional;
  }

  const kind = isPythonProperty(member) ? 'property' : 'method';
  return {
    kind,
    name: toSnakeCase(member.alias),
    isAsync: !!member.async && !isEventContextManager,
    positional,
    keywordOnly,
    returnType,
    comment: renderSpec(member.spec),
    documented: true,
  };
}

/**
 * @param {string} className
 * @param {any} extra
 * @returns {PyMember}
 */
function buildExtraMember(className, extra) {
  const place = `${className}.${extra.name}`;
  const returnDocsType = Type.parse(extra.returns);
  return {
    kind: extra.kind,
    name: extra.name,
    isAsync: extra.async,
    positional: extra.args.map(arg => ({
      name: toSnakeCase(arg.name),
      implName: arg.name,
      type: toPy(Type.parse(arg.type), { dir: 'in', place: `${place}.${arg.name}` }),
      optional: false,
      comment: '',
      deprecated: undefined,
      documented: false,
    })),
    keywordOnly: [],
    returnType: returnDocsType.name === 'void' ? null : toPy(returnDocsType, { dir: 'out', place }),
    comment: null,
    documented: false,
  };
}

/**
 * @param {any} clazz
 * @returns {PyClass}
 */
function buildClass(clazz) {
  let base = BASE_CLASS;
  if (rules.contextManagerClasses.includes(clazz.name))
    base = CONTEXT_MANAGER_CLASS;
  else if (clazz.extends && generatedClassNames.has(clazz.extends))
    base = clazz.extends;
  const members = [];
  for (const member of clazz.membersArray) {
    if (member.kind === 'event')
      continue;
    members.push(buildMember(clazz, member));
  }
  for (const extra of lookupRule('extraMembers', clazz.name) || [])
    members.push(buildExtraMember(clazz.name, extra));
  members.sort((a, b) => byName(a.name, b.name));
  const events = [...clazz.eventsArray].sort((a, b) => byName(a.name.toLowerCase(), b.name.toLowerCase()));
  return { name: clazz.name, base, events, members };
}

/** Classes in alphabetical order, with base classes first. */
function orderedClasses() {
  const classes = documentation.classesArray.filter(c => generatedClassNames.has(c.name)).sort((a, b) => byName(a.name, b.name));
  const result = [];
  const done = new Set();
  const visit = clazz => {
    if (done.has(clazz.name))
      return;
    if (clazz.extends && generatedClassNames.has(clazz.extends))
      visit(documentation.classes.get(clazz.extends));
    done.add(clazz.name);
    result.push(clazz);
  };
  classes.forEach(visit);
  return result;
}

// ---------------------------------------------------------------------------
// Output.

const LICENSE = `# Copyright (c) Microsoft Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
`;

/** @param {any} event */
function eventPayload(clazz, event) {
  let payload = docType(toPy(event.type, { dir: 'out', place: `${clazz.name}.${event.name}` }));
  if (payload.startsWith('{'))
    payload = 'typing.Dict';
  return payload.replace(/Union\[/g, 'typing.Union[');
}

/**
 * on() or once(), with one typed overload per event.
 * @param {PyClass} clazz
 * @param {'on' | 'once'} method
 * @param {string[]} out
 */
function emitEventMethod(clazz, method, out) {
  const events = clazz.events;
  const handlerReturn = isAsync ? 'typing.Union[typing.Awaitable[None], None]' : 'None';
  for (const event of events) {
    out.push('    @typing.overload');
    out.push(`    def ${method}(self, event: Literal['${event.name.toLowerCase()}'], f: typing.Callable[['${eventPayload(clazz, event)}'], '${handlerReturn}']) -> None:`);
    out.push(`        """${formatComment(renderSpec(event.spec), ' '.repeat(8))}"""`);
  }
  if (events.length === 1) {
    out.push('    @typing.overload');
    out.push(`    def ${method}(self, event: str, f: typing.Callable[...,${handlerReturn}]) -> None: ...`);
    out.push('');
  }
  out.push(`    def ${method}(self, event: str, f: typing.Callable[...,${handlerReturn}]) -> None:`);
  out.push(`        return super().${method}(event=event,f=f)`);
}

/**
 * Typed overloads of expect_event() / wait_for_event(), keyed on the event name.
 * @param {PyClass} clazz
 * @param {string} methodName
 * @param {string[]} out
 */
function emitEventOverloads(clazz, methodName, out) {
  if (!clazz.events.length)
    return;
  const isExpect = methodName === 'expect_event';
  const asyncPrefix = !isExpect && isAsync ? 'async ' : '';
  for (const event of clazz.events) {
    const payload = eventPayload(clazz, event);
    const returnType = isExpect ? `${EVENT_CONTEXT_MANAGER_CLASS}["${payload}"]` : `"${payload}"`;
    out.push('    @typing.overload');
    out.push(`    ${asyncPrefix}def ${methodName}(`);
    out.push('        self,');
    out.push(`        event: typing.Literal["${event.name.toLowerCase()}"],`);
    out.push(`        predicate: typing.Optional[typing.Callable[["${payload}"], bool]] = None,`);
    out.push('        *,');
    out.push('        timeout: typing.Optional[float] = None,');
    out.push(`    ) -> ${returnType}: ...`);
    out.push('');
  }
  const catchAllReturn = isExpect ? `${EVENT_CONTEXT_MANAGER_CLASS}[typing.Any]` : 'typing.Any';
  out.push('    @typing.overload');
  out.push(`    ${asyncPrefix}def ${methodName}(`);
  out.push('        self,');
  out.push('        event: str,');
  out.push('        predicate: typing.Optional[typing.Callable[..., bool]] = None,');
  out.push('        *,');
  out.push('        timeout: typing.Optional[float] = None,');
  out.push(`    ) -> ${catchAllReturn}: ...`);
  out.push('');
}

/** @param {PyParam} param */
function paramAnnotation(param) {
  let type = param.type;
  if (param.implName === 'timeout' && type.kind === 'name' && type.name === 'float')
    type = makeUnion([NAME('float'), NAME('datetime.timedelta')]);
  if (param.optional && !(type.kind === 'union' && type.members?.some(isNone)))
    type = { kind: 'union', members: [type, NONE] };
  return annotation(type) + (param.optional ? ' = None' : '');
}

/**
 * @param {PyClass} clazz
 * @param {PyMember} member
 */
function emitDocstring(clazz, member, out) {
  const indent = ' '.repeat(8);
  out.push(`${indent}"""${clazz.name}.${member.name}`);
  if (member.comment)
    out.push(`${indent}${formatComment(member.comment, indent)}`);
  const params = [...member.positional, ...member.keywordOnly].filter(p => p.documented);
  if (params.length) {
    out.push('');
    out.push(`${indent}Parameters`);
    out.push(`${indent}----------`);
    for (const param of params) {
      const type = param.optional ? makeOptional(docType(param.type)) : docType(param.type);
      out.push(`${indent}${param.name} : ${type}`);
      if (param.comment)
        out.push(`${indent}    ${indentParagraph(escapeBackslashes(param.comment), indent + '    ')}`);
      if (param.deprecated)
        out.push(`${indent}    Deprecated: ${escapeBackslashes(param.deprecated)}`);
    }
  }
  if (member.returnType) {
    out.push('');
    out.push(`${indent}Returns`);
    out.push(`${indent}-------`);
    out.push(`${indent}${docType(member.returnType)}`);
  }
  out.push(`${indent}"""`);
}

/**
 * @param {PyClass} clazz
 * @param {PyMember} member
 * @param {string[]} out
 */
function emitMember(clazz, member, out) {
  const returnAnnotation = member.returnType ? annotation(member.returnType) : 'None';
  const wrapper = returnWrapper(member.returnType);
  if (member.kind === 'property') {
    out.push('    @property');
    out.push(`    def ${member.name}(self) -> ${returnAnnotation}:`);
    if (member.documented)
      emitDocstring(clazz, member, out);
    out.push(`        return ${wrapper}(self._impl_obj.${member.name})`);
    return;
  }

  const params = ['self', ...member.positional.map(p => `${p.name}: ${paramAnnotation(p)}`)];
  if (member.keywordOnly.length)
    params.push('*', ...member.keywordOnly.map(p => `${p.name}: ${paramAnnotation(p)}`));
  out.push(`    ${member.isAsync && isAsync ? 'async ' : ''}def ${member.name}(${params.join(', ')}) -> ${returnAnnotation}:`);
  if (member.documented)
    emitDocstring(clazz, member, out);
  if (rules.tracebackHideClasses.includes(clazz.name))
    out.push('        __tracebackhide__ = True');

  // Dunder methods take positional arguments only.
  const isDunder = member.name.startsWith('__');
  const callArgs = [...member.positional, ...member.keywordOnly].map(p => isDunder ? forwardExpression(p) : `${p.implName}=${forwardExpression(p)}`).join(', ');
  const call = `self._impl_obj.${member.name}(${callArgs})`;
  if (member.returnType?.kind === 'ecm') {
    if (isAsync) {
      out.push('');
      out.push(`        return AsyncEventContextManager(${call}.future)`);
    } else {
      out.push(`        return EventContextManager(self, ${call}.future)`);
    }
    return;
  }
  out.push('');
  let expression = call;
  if (member.isAsync)
    expression = isAsync ? `await ${call}` : `self._sync(${call})`;
  if (member.returnType)
    out.push(`        return ${wrapper}(${expression})`);
  else
    out.push(`        ${expression}`);
}

/**
 * @param {PyClass} clazz
 * @param {string[]} out
 */
function emitClass(clazz, out) {
  out.push('');
  out.push(`class ${clazz.name}(${clazz.base}):`);
  // Typed, so that mypy checks every call below against the implementation.
  out.push(`    _impl_obj: ${clazz.name}Impl`);
  out.push('');
  /** @type {{ name: string, emit: () => void }[]} */
  const items = clazz.members.map(member => ({
    name: member.name,
    emit: () => {
      if (member.name === 'expect_event' || member.name === 'wait_for_event')
        emitEventOverloads(clazz, member.name, out);
      emitMember(clazz, member, out);
    },
  }));
  if (clazz.events.length) {
    for (const method of /** @type {const} */ (['on', 'once']))
      items.push({ name: method, emit: () => emitEventMethod(clazz, method, out) });
  }
  items.sort((a, b) => byName(a.name, b.name));
  for (const item of items) {
    out.push('');
    item.emit();
  }
  out.push('');
  out.push(`mapping.register(${clazz.name}Impl, ${clazz.name})`);
}

// ---------------------------------------------------------------------------
// The public TypedDicts (playwright/_impl/_api_structures.py).

/**
 * The fields of one use of a struct, as Python annotation text.
 * @param {PyType} t
 */
function structFields(t) {
  return t.docType.properties.map(p => {
    const place = `${t.place}.${p.name}`;
    const type = toPy(p.type, { dir: t.dir || 'out', place });
    if (someType(type, c => c.kind === 'class' && !!c.wrapper))
      errors.push(`The struct field ${place} refers to a class; _api_structures.py cannot import it`);
    const text = annotation(type);
    const optional = !p.required;
    return { name: p.name, optional, text: optional && !text.startsWith('typing.Optional[') ? `typing.Optional[${text}]` : text };
  });
}

/**
 * Every struct that the API uses, with its fields. Nested structs are found
 * while the fields are rendered.
 */
function buildStructs() {
  /** @type {Map<string, { fields: { name: string, optional: boolean, text: string }[] }>} */
  const structs = new Map();
  for (let pending = [...structUses.keys()]; pending.length; pending = [...structUses.keys()].filter(name => !structs.has(name))) {
    for (const name of pending) {
      const uses = /** @type {PyType[]} */ (structUses.get(name));
      // A struct used for input and output takes the output types:
      // `List` rather than `Sequence`, `pathlib.Path` rather than `str | Path`.
      const dir = uses.some(use => use.dir === 'out') ? 'out' : 'in';
      const fields = structFields({ ...uses[0], dir });
      const key = JSON.stringify(fields);
      for (const use of uses.slice(1)) {
        if (JSON.stringify(structFields({ ...use, dir })) !== key)
          errors.push(`The struct ${name} has different fields at ${uses[0].place} and ${use.place}`);
      }
      structs.set(name, { fields });
    }
  }
  return structs;
}

/**
 * Struct names in alphabetical order, each after the structs that its fields
 * use: the annotations are evaluated when the class is created.
 * @param {Map<string, { fields: { text: string }[] }>} structs
 */
function orderedStructNames(structs) {
  const result = [];
  const done = new Set();
  const visit = name => {
    if (done.has(name))
      return;
    done.add(name);
    const text = /** @type {any} */ (structs.get(name)).fields.map(f => f.text).join(' ');
    for (const other of [...structs.keys()].sort(byName)) {
      if (other !== name && new RegExp(`\\b${other}\\b`).test(text))
        visit(other);
    }
    result.push(name);
  };
  [...structs.keys()].sort(byName).forEach(visit);
  return result;
}

function emitStructs() {
  const structs = buildStructs();
  const body = [];
  for (const name of orderedStructNames(structs)) {
    const { fields } = /** @type {any} */ (structs.get(name));
    const totalRule = lookupRule('structTotal', name);
    const total = totalRule !== undefined ? totalRule : !fields.some(f => f.optional);
    body.push('', '', `class ${name}(TypedDict${total ? '' : ', total=False'}):`);
    for (const field of fields)
      body.push(`    ${field.name}: ${field.text.replace(/\btyping\./g, '').replace(/\bpathlib\.Path\b/g, 'Path')}`);
  }
  const text = body.join('\n');
  const typingNames = ['Any', 'Dict', 'List', 'Literal', 'Optional', 'Pattern', 'Sequence', 'TypedDict', 'Union'].filter(n => new RegExp(`\\b${n}\\b`).test(text));
  const header = [LICENSE, '# Generated from the docs by scripts/codegen/generate_api.js. Do not edit.', ''];
  if (/\bPath\b/.test(text))
    header.push('from pathlib import Path');
  header.push(`from typing import ${typingNames.join(', ')}`);
  return [...header, text, ''].join('\n');
}

function checkRules() {
  for (const table of ['extraMembers', 'extraOptions', 'structTotal']) {
    for (const key of Object.keys(/** @type {any} */ (rules)[table])) {
      if (!usedRules.has(`${table}:${key}`))
        errors.push(`${table}: the entry "${key}" no longer matches anything; remove it`);
    }
  }
  for (const table of ['handWrittenClasses', 'contextManagerClasses', 'tracebackHideClasses']) {
    for (const name of /** @type {any} */ (rules)[table]) {
      if (!documentation.classes.has(name))
        errors.push(`${table}: the docs have no class ${name}`);
    }
  }
}

function main() {
  const classes = orderedClasses().map(buildClass);
  const body = [];
  for (const clazz of classes)
    emitClass(clazz, body);

  const header = [LICENSE, '', 'import typing', 'import pathlib', 'import datetime', '', 'from typing import Literal', ''];
  if (usedStructs.size)
    header.push(`from playwright._impl._api_structures import ${[...usedStructs].sort().join(', ')}`);
  for (const clazz of classes)
    header.push(`from playwright._impl._api_classes import ${clazz.name} as ${clazz.name}Impl`);
  header.push('from playwright._impl._errors import Error');
  header.push('from playwright._impl._form_data import FormData');
  header.push('from playwright._impl._helper import to_milliseconds');
  if (isAsync)
    header.push('from playwright._impl._async_base import AsyncEventContextManager, AsyncBase, AsyncContextManager, mapping');
  else
    header.push('from playwright._impl._sync_base import EventContextManager, SyncBase, SyncContextManager, mapping');

  // Every flavor builds the structs, so that every run checks them.
  const structsText = emitStructs();
  const text = options.flavor === 'structs' ? structsText : [...header, ...body, ''].join('\n');

  checkRules();
  if (errors.length) {
    for (const error of errors)
      console.error(error);
    process.exit(1);
  }

  if (options.out)
    fs.writeFileSync(options.out, text);
  else
    process.stdout.write(text);
}

main();
