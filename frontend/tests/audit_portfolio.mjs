import { readFile, readdir } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
const root=fileURLToPath(new URL('../portfolio-dist/',import.meta.url))
const forbidden=[/\/api\/(auth|me|patients|appointments|visits|billing)/,/postgres(?:ql)?(?:\+psycopg)?:\/\//i,/-----BEGIN .*PRIVATE KEY-----/,/\bgh[pousr]_[A-Za-z0-9]{30,}/,/\bAKIA[A-Z0-9]{16}\b/,/\bsk-(?:proj-)?[A-Za-z0-9_-]{40,}\b/,/neon\.tech|onrender\.com/i]
const files=await readdir(root,{recursive:true,withFileTypes:true})
let count=0
for(const entry of files){if(!entry.isFile())continue;const name=path.join(entry.parentPath,entry.name);assert.ok(/\.(html|js|css|svg)$/.test(name),'Unexpected published asset type');const content=await readFile(name,'utf8');for(const pattern of forbidden)assert.ok(!pattern.test(content),'Forbidden network/secret pattern in '+entry.name);assert.ok(!/\.env|\.pem|\.dump|\.sql$/.test(entry.name));count++;createHash('sha256').update(content).digest('hex')}
const index=await readFile(path.join(root,'index.html'),'utf8')
assert.ok(index.includes("connect-src 'none'"),'Missing no-network CSP')
assert.ok(index.includes('/clinc-final/assets/'),'Wrong asset base')
assert.ok(index.includes('lang="ar" dir="rtl"'),'Missing Arabic RTL')
console.log(`PASS portfolio asset audit: ${count} allowed static assets; no real API routes, backend URLs or secret-format findings`)
