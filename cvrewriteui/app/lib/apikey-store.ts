// Encrypted, browser-only storage for the user's Anthropic API key (BYOK).
//
// The key is encrypted with AES-256-GCM and kept in IndexedDB — never in
// localStorage or plain text. The AES key is derived (PBKDF2) from a random
// per-device seed, so the ciphertext is useless without this browser's seed.
//
// All access is inside async functions (never at module load) so this stays
// safe under SSR/prerender, where `indexedDB` and `crypto.subtle` don't exist.

const DB_NAME = "cvrewrite"
const STORE = "keyval"
const SEED_KEY = "device_seed"
const KEY_RECORD = "anthropic_api_key"
const PBKDF2_ITERATIONS = 100_000

interface StoredKey {
  id: string
  salt: ArrayBuffer
  iv: ArrayBuffer
  ciphertext: ArrayBuffer
}

function isAvailable(): boolean {
  return (
    typeof indexedDB !== "undefined" &&
    typeof crypto !== "undefined" &&
    typeof crypto.subtle !== "undefined"
  )
}

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1)
    req.onupgradeneeded = () => {
      const db = req.result
      if (!db.objectStoreNames.contains(STORE)) db.createObjectStore(STORE)
    }
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error ?? new Error("Failed to open IndexedDB"))
  })
}

async function withStore<T>(
  mode: IDBTransactionMode,
  run: (store: IDBObjectStore) => IDBRequest<T>,
): Promise<T> {
  const db = await openDb()
  try {
    return await new Promise<T>((resolve, reject) => {
      const req = run(db.transaction(STORE, mode).objectStore(STORE))
      req.onsuccess = () => resolve(req.result)
      req.onerror = () => reject(req.error ?? new Error("IndexedDB request failed"))
    })
  } finally {
    db.close()
  }
}

function idbGet<T>(key: string): Promise<T | undefined> {
  return withStore<T | undefined>("readonly", (s) => s.get(key) as IDBRequest<T | undefined>)
}

function idbPut(key: string, value: unknown): Promise<IDBValidKey> {
  return withStore("readwrite", (s) => s.put(value, key))
}

function idbDelete(key: string): Promise<undefined> {
  return withStore("readwrite", (s) => s.delete(key) as IDBRequest<undefined>)
}

async function getDeviceSeed(): Promise<ArrayBuffer> {
  const existing = await idbGet<ArrayBuffer>(SEED_KEY)
  if (existing) return existing
  const seed = crypto.getRandomValues(new Uint8Array(32))
  await idbPut(SEED_KEY, seed.buffer)
  return seed.buffer
}

async function deriveKey(seed: ArrayBuffer, salt: ArrayBuffer): Promise<CryptoKey> {
  const base = await crypto.subtle.importKey("raw", seed, "PBKDF2", false, ["deriveKey"])
  return crypto.subtle.deriveKey(
    { name: "PBKDF2", salt, iterations: PBKDF2_ITERATIONS, hash: "SHA-256" },
    base,
    { name: "AES-GCM", length: 256 },
    false,
    ["encrypt", "decrypt"],
  )
}

/** Encrypt and store the API key. Throws if secure storage is unavailable. */
export async function saveApiKey(key: string): Promise<void> {
  if (!isAvailable()) {
    throw new Error(
      "Secure storage is unavailable. Use a modern browser over HTTPS (or localhost).",
    )
  }
  const seed = await getDeviceSeed()
  const salt = crypto.getRandomValues(new Uint8Array(16))
  const iv = crypto.getRandomValues(new Uint8Array(12))
  const cryptoKey = await deriveKey(seed, salt.buffer)
  const ciphertext = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv },
    cryptoKey,
    new TextEncoder().encode(key),
  )
  const record: StoredKey = {
    id: KEY_RECORD,
    salt: salt.buffer,
    iv: iv.buffer,
    ciphertext,
  }
  await idbPut(KEY_RECORD, record)
}

/** Decrypt and return the stored API key, or null if none / undecryptable. */
export async function loadApiKey(): Promise<string | null> {
  if (!isAvailable()) return null
  try {
    const record = await idbGet<StoredKey>(KEY_RECORD)
    const seed = await idbGet<ArrayBuffer>(SEED_KEY)
    if (!record || !seed) return null
    const cryptoKey = await deriveKey(seed, record.salt)
    const plain = await crypto.subtle.decrypt(
      { name: "AES-GCM", iv: record.iv },
      cryptoKey,
      record.ciphertext,
    )
    return new TextDecoder().decode(plain)
  } catch {
    return null
  }
}

/** Remove the stored API key (leaves the device seed in place). */
export async function deleteApiKey(): Promise<void> {
  if (!isAvailable()) return
  try {
    await idbDelete(KEY_RECORD)
  } catch {
    /* nothing stored / storage unavailable — treat as already gone */
  }
}

/** Whether an encrypted key is present (does not attempt to decrypt it). */
export async function hasApiKey(): Promise<boolean> {
  if (!isAvailable()) return false
  try {
    return (await idbGet<StoredKey>(KEY_RECORD)) !== undefined
  } catch {
    return false
  }
}
