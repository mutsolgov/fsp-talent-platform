#!/usr/bin/env node
/**
 * FSP IT-Talent Platform — 100% Offline Test Runner
 * Uses Node 22 native test runner (node:test, node:assert/strict) + Sucrase transpilation.
 * Follows Ponytail principle: zero external npm dependencies, pure stdlib/platform first.
 */

import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';
import { createRequire } from 'module';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const frontendRoot = path.resolve(__dirname, '..');
const srcDir = path.join(frontendRoot, 'src');
const testsDir = path.join(srcDir, '__tests__');

// Ensure module resolution sees local vendor, node_modules, and npx cache
const localVendorDir = path.join(__dirname, 'vendor');
const localNodeModules = path.join(frontendRoot, 'node_modules');
const npxVendorDir = path.resolve(process.env.HOME || '/home/muhammad', '.npm/_npx/668c188756b835f3/node_modules');
process.env.NODE_PATH = [localVendorDir, localNodeModules, npxVendorDir, process.env.NODE_PATH || ''].filter(Boolean).join(':');

const require = createRequire(import.meta.url);
require('module').Module._initPaths();

// -----------------------------------------------------------------------------
// 1. Setup DOM & Browser Global Mocks for Offline SSR & State Tests
// -----------------------------------------------------------------------------
class MockStorage {
  constructor() {
    this.store = {};
  }
  getItem(key) {
    return this.store[key] !== undefined ? this.store[key] : null;
  }
  setItem(key, value) {
    this.store[key] = String(value);
  }
  removeItem(key) {
    delete this.store[key];
  }
  clear() {
    this.store = {};
  }
  get length() {
    return Object.keys(this.store).length;
  }
  key(index) {
    return Object.keys(this.store)[index] || null;
  }
}

const windowEventListeners = {};
const documentEventListeners = {};

const mockLocalStorage = new MockStorage();

global.window = {
  localStorage: mockLocalStorage,
  location: {
    pathname: '/',
    search: '',
    hash: '',
    origin: 'http://localhost:3000',
    href: 'http://localhost:3000/',
  },
  history: {
    pushState: (state, title, url) => {
      if (url) {
        global.window.location.pathname = url.split('?')[0];
      }
    },
    replaceState: (state, title, url) => {
      if (url) {
        global.window.location.pathname = url.split('?')[0];
      }
    },
  },
  scrollTo: () => {},
  addEventListener: (event, handler) => {
    windowEventListeners[event] = windowEventListeners[event] || [];
    windowEventListeners[event].push(handler);
  },
  removeEventListener: (event, handler) => {
    if (windowEventListeners[event]) {
      windowEventListeners[event] = windowEventListeners[event].filter((h) => h !== handler);
    }
  },
  dispatchEvent: (event) => {
    const list = windowEventListeners[event.type] || [];
    list.forEach((h) => {
      try {
        h(event);
      } catch (err) {
        console.error(err);
      }
    });
  },
};

global.localStorage = mockLocalStorage;

global.document = {
  title: 'FSP Talent Platform',
  addEventListener: (event, handler) => {
    documentEventListeners[event] = documentEventListeners[event] || [];
    documentEventListeners[event].push(handler);
  },
  removeEventListener: (event, handler) => {
    if (documentEventListeners[event]) {
      documentEventListeners[event] = documentEventListeners[event].filter((h) => h !== handler);
    }
  },
  dispatchEvent: (event) => {
    const list = documentEventListeners[event.type] || [];
    list.forEach((h) => {
      try {
        h(event);
      } catch (err) {
        console.error(err);
      }
    });
  },
  createElement: (tag) => ({
    tagName: tag.toUpperCase(),
    style: {},
    setAttribute: () => {},
    getAttribute: () => null,
  }),
  body: {
    appendChild: () => {},
    removeChild: () => {},
  },
};

if (!global.navigator) {
  try {
    Object.defineProperty(global, 'navigator', {
      value: { userAgent: 'node' },
      configurable: true,
      writable: true,
    });
  } catch {
    // navigator getter already present in Node 22
  }
}

global.KeyboardEvent = class KeyboardEvent {
  constructor(type, init = {}) {
    this.type = type;
    this.key = init.key || '';
    this.code = init.code || '';
    this.altKey = !!init.altKey;
    this.ctrlKey = !!init.ctrlKey;
    this.shiftKey = !!init.shiftKey;
    this.metaKey = !!init.metaKey;
  }
};

global.CustomEvent = class CustomEvent {
  constructor(type, init = {}) {
    this.type = type;
    this.detail = init.detail;
  }
};

// -----------------------------------------------------------------------------
// 2. Setup Sucrase On-The-Fly Transpilation for .ts and .tsx Files
// -----------------------------------------------------------------------------
let sucrase;
try {
  sucrase = require(path.join(npxVendorDir, 'sucrase'));
} catch {
  sucrase = require('sucrase');
}

require.extensions['.ts'] = (module, filename) => {
  const content = fs.readFileSync(filename, 'utf8');
  const compiled = sucrase.transform(content, {
    transforms: ['typescript', 'imports'],
    filePath: filename,
  }).code;
  module._compile(compiled, filename);
};

require.extensions['.tsx'] = (module, filename) => {
  const content = fs.readFileSync(filename, 'utf8');
  const compiled = sucrase.transform(content, {
    transforms: ['typescript', 'jsx', 'imports'],
    filePath: filename,
  }).code;
  module._compile(compiled, filename);
};

require.extensions['.css'] = (module) => {
  module.exports = {};
};
require.extensions['.svg'] = (module) => {
  module.exports = 'mock-fsp-logo.svg';
};
require.extensions['.png'] = (module) => {
  module.exports = 'mock-fsp-image.png';
};
require.extensions['.woff2'] = (module) => {
  module.exports = 'mock-font.woff2';
};
require.extensions['.ttf'] = (module) => {
  module.exports = 'mock-font.ttf';
};

// -----------------------------------------------------------------------------
// 3. Test Runner Primitives & Assertion Matchers
// -----------------------------------------------------------------------------
const nodeTest = require('node:test');
const assert = require('node:assert/strict');
const ReactDOMServer = require(path.join(npxVendorDir, 'react-dom/server'));

global.describe = nodeTest.describe;
global.it = nodeTest.it;
global.test = nodeTest.test;
global.before = nodeTest.before;
global.after = nodeTest.after;
global.beforeEach = nodeTest.beforeEach;
global.afterEach = nodeTest.afterEach;
global.assert = assert;
global.renderToString = ReactDOMServer.renderToString;

function createMatcher(actual) {
  return {
    toBe(expected) {
      assert.strictEqual(actual, expected);
    },
    toEqual(expected) {
      assert.deepStrictEqual(actual, expected);
    },
    toBeTruthy() {
      assert.ok(actual, `Expected ${actual} to be truthy`);
    },
    toBeFalsy() {
      assert.ok(!actual, `Expected ${actual} to be falsy`);
    },
    toBeNull() {
      assert.strictEqual(actual, null);
    },
    toBeUndefined() {
      assert.strictEqual(actual, undefined);
    },
    toBeDefined() {
      assert.notStrictEqual(actual, undefined);
    },
    toContain(item) {
      if (typeof actual === 'string') {
        const cleanActual = actual.replace(/<!-- -->/g, '');
        assert.ok(
          cleanActual.includes(item) || actual.includes(item),
          `Expected to contain ${JSON.stringify(item)}, got ${JSON.stringify(actual)}`
        );
      } else if (Array.isArray(actual)) {
        assert.ok(actual.includes(item), `Expected to contain ${JSON.stringify(item)}, got ${JSON.stringify(actual)}`);
      } else if (actual && typeof actual === 'object') {
        assert.ok(item in actual, `Expected key ${item} in ${JSON.stringify(actual)}`);
      } else {
        assert.fail(`Cannot check toContain on ${typeof actual}`);
      }
    },
    toBeGreaterThan(val) {
      assert.ok(actual > val, `Expected ${actual} > ${val}`);
    },
    toBeGreaterThanOrEqual(val) {
      assert.ok(actual >= val, `Expected ${actual} >= ${val}`);
    },
    toBeLessThan(val) {
      assert.ok(actual < val, `Expected ${actual} < ${val}`);
    },
    toBeLessThanOrEqual(val) {
      assert.ok(actual <= val, `Expected ${actual} <= ${val}`);
    },
    toMatch(pattern) {
      const regex = typeof pattern === 'string' ? new RegExp(pattern) : pattern;
      assert.ok(regex.test(String(actual)), `Expected "${actual}" to match ${regex}`);
    },
    toHaveLength(len) {
      assert.strictEqual(actual?.length, len);
    },
    toThrow(expected) {
      assert.throws(() => {
        if (typeof actual === 'function') actual();
      }, expected);
    },
    get not() {
      return {
        toBe(expected) {
          assert.notStrictEqual(actual, expected);
        },
        toEqual(expected) {
          assert.notDeepStrictEqual(actual, expected);
        },
        toBeTruthy() {
          assert.ok(!actual);
        },
        toBeFalsy() {
          assert.ok(actual);
        },
        toBeNull() {
          assert.notStrictEqual(actual, null);
        },
        toBeUndefined() {
          assert.notStrictEqual(actual, undefined);
        },
        toContain(item) {
          assert.ok(!actual.includes(item), `Expected not to contain ${JSON.stringify(item)}`);
        },
        toMatch(pattern) {
          const regex = typeof pattern === 'string' ? new RegExp(pattern) : pattern;
          assert.ok(!regex.test(String(actual)), `Expected "${actual}" not to match ${regex}`);
        },
        toThrow() {
          assert.doesNotThrow(() => {
            if (typeof actual === 'function') actual();
          });
        },
      };
    },
  };
}

global.expect = createMatcher;

function fn(impl) {
  const calls = [];
  const mock = function (...args) {
    calls.push(args);
    return impl ? impl(...args) : undefined;
  };
  mock.calls = calls;
  mock.mock = {
    calls,
    get lastCall() {
      return calls[calls.length - 1];
    },
  };
  return mock;
}

global.vi = { fn };
global.jest = { fn };

// -----------------------------------------------------------------------------
// 4. Discover and Execute Test Suites
// -----------------------------------------------------------------------------
console.log('='.repeat(80));
console.log('FSP IT-TALENT PLATFORM — FRONTEND TEST RUNNER');
console.log(`Directory: ${testsDir}`);
console.log(`Node: ${process.version} (Native node:test runner)`);
console.log('='.repeat(80));

if (!fs.existsSync(testsDir)) {
  console.error(`Tests directory does not exist: ${testsDir}`);
  process.exit(1);
}

const testFiles = fs
  .readdirSync(testsDir)
  .filter((f) => f.endsWith('.test.ts') || f.endsWith('.test.tsx'))
  .sort();

console.log(`Discovered ${testFiles.length} test suite(s):`);
testFiles.forEach((f, idx) => console.log(`  [${idx + 1}] ${f}`));
console.log('-'.repeat(80));

for (const file of testFiles) {
  const filePath = path.join(testsDir, file);
  try {
    require(filePath);
  } catch (err) {
    console.error(`Failed to load test suite ${file}:`, err);
    process.exitCode = 1;
  }
}
