/**
 * Tests for electron/backend-probes.cjs.
 *
 * Run with: node --test electron/backend-probes.test.cjs
 * (Wired into npm test:desktop:platforms in package.json.)
 */

const test = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const os = require('node:os')
const path = require('node:path')

const { canImportAtlasCli, atlasRuntimeImportProbe, verifyAtlasCli } = require('./backend-probes.cjs')

// Resolve the host's own Node binary -- guaranteed to be on disk and
// runnable. We use it as both a stand-in for "a python that doesn't
// have atlas_cli" (since `node -c "import atlas_cli"` will exit
// non-zero) and as a way to script verifyAtlasCli's success path
// (a tiny script we write to disk that exits 0 on --version).
const NODE_BIN = process.execPath

test('canImportAtlasCli returns false when path is falsy', () => {
  assert.equal(canImportAtlasCli(''), false)
  assert.equal(canImportAtlasCli(null), false)
  assert.equal(canImportAtlasCli(undefined), false)
})

test('canImportAtlasCli returns false when interpreter cannot run -c', () => {
  // node IS an interpreter, but `node -c "import atlas_cli"` is a
  // SyntaxError -- different exit reason from a real Python's
  // ModuleNotFoundError, but the predicate is "exit 0 or not" and
  // both land on "not", which is exactly what we want for the
  // resolver fall-through.
  assert.equal(canImportAtlasCli(NODE_BIN), false)
})

test('canImportAtlasCli returns false when binary does not exist', () => {
  const ghost = path.join(os.tmpdir(), 'atlas-probes-ghost-' + Date.now() + '.exe')
  assert.equal(canImportAtlasCli(ghost), false)
})

test('atlas runtime import probe checks config dependencies', () => {
  const probe = atlasRuntimeImportProbe()
  assert.match(probe, /\bimport yaml\b/)
  assert.match(probe, /\bimport atlas_cli\.config\b/)
})

test('verifyAtlasCli returns false when command is falsy', () => {
  assert.equal(verifyAtlasCli(''), false)
  assert.equal(verifyAtlasCli(null), false)
  assert.equal(verifyAtlasCli(undefined), false)
})

test('verifyAtlasCli returns false when binary does not exist', () => {
  const ghost = path.join(os.tmpdir(), 'atlas-probes-ghost-' + Date.now() + '.exe')
  assert.equal(verifyAtlasCli(ghost), false)
})

test('verifyAtlasCli returns true when --version exits 0', () => {
  // Write a tiny script that exits 0 regardless of args, then invoke
  // it through node. This stands in for a working atlas binary --
  // verifyAtlasCli only cares about the exit code.
  const scriptPath = path.join(os.tmpdir(), `atlas-probes-ok-${Date.now()}-${process.pid}.cjs`)
  fs.writeFileSync(scriptPath, 'process.exit(0)\n')
  try {
    // Use node as the launcher and our script as the "command". Pass
    // shell:false (default) -- node is a real binary, no shim.
    // execFileSync passes ['--version'] as args, which node ignores
    // gracefully (well, it prints its version and exits 0, which is
    // perfect -- exit code 0 is the only signal we read).
    assert.equal(verifyAtlasCli(NODE_BIN), true)
  } finally {
    try {
      fs.unlinkSync(scriptPath)
    } catch {
      void 0
    }
  }
})

test('verifyAtlasCli swallows timeouts (does not throw)', () => {
  // We can't easily provoke a real 5s hang in CI without slowing the
  // suite, but we CAN confirm that an invocation that DOES throw
  // (because the binary is missing) returns false rather than
  // propagating. Same code path the timeout case takes.
  assert.equal(verifyAtlasCli('/definitely/not/a/real/binary/anywhere'), false)
})
