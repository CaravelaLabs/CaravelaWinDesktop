// electron-builder collects production node_modules with `pnpm list --depth Infinity`
// and then holds that graph in the packer process. On a 32GB Windows host that walk
// dies at the 16GB V8 ceiling (exit 134) before the app is packed. The desktop bundle
// externalizes only node-pty and get-windows; before-pack.mjs stages those into
// dist/node_modules. Re-apply this skip on every pack: `pnpm install` during Update
// restores the stock collector.
import fs from 'node:fs'
import path from 'node:path'

export const WALK_SKIP_MARKER = 'Caravela: skip unbounded pnpm production walk'

const OPEN = 'async getNodeModules({ packageName, archFilter, ignoredDependencies, }) {\n        const tree = await this.getDependenciesTree(this.installOptions.manager);'

const STUBBED = `async getNodeModules({ packageName, archFilter, ignoredDependencies, }) {
        // ${WALK_SKIP_MARKER}. pnpm list --depth Infinity OOMs the packer on a 32GB Windows host.
        // Native modules are staged into dist/node_modules by before-pack.mjs.
        return { nodeModules: [{ name: "react", version: "19.3.0", excluded: true }], logSummary: {} };
        const tree = await this.getDependenciesTree(this.installOptions.manager);`

/** @param {string} text @returns {{ text: string, changed: boolean }} */
export function patchCollectorSource(text) {
  if (text.includes(WALK_SKIP_MARKER) || !text.includes(OPEN)) return { text, changed: false }
  return { text: text.replace(OPEN, STUBBED), changed: true }
}

/**
 * Patch every on-disk app-builder-lib collector under the checkout.
 * pnpm hardlinks these; the inode set makes a second write a no-op.
 * @param {string} repoRoot @returns {number} files whose bytes changed
 */
export function skipUnboundedNodeModuleWalk(repoRoot) {
  const pnpm = path.join(repoRoot, 'node_modules', '.pnpm')
  if (!fs.existsSync(pnpm)) return 0
  const seen = new Set()
  let patched = 0
  for (const dir of fs.readdirSync(pnpm)) {
    if (!dir.startsWith('app-builder-lib@') && !dir.startsWith('electron-builder@') && !dir.startsWith('dmg-builder@') && !dir.startsWith('electron-builder-squirrel-')) continue
    const file = path.join(pnpm, dir, 'node_modules', 'app-builder-lib', 'dist', 'node-module-collector', 'nodeModulesCollector.js')
    if (!fs.existsSync(file)) continue
    let stat
    try { stat = fs.statSync(file) } catch { continue }
    const key = `${stat.dev}:${stat.ino}`
    if (seen.has(key)) continue
    seen.add(key)
    const original = fs.readFileSync(file, 'utf8')
    const next = patchCollectorSource(original)
    if (!next.changed) continue
    fs.writeFileSync(file, next.text)
    patched++
  }
  return patched
}
