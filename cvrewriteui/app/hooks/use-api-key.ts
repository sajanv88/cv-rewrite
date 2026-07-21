import { useCallback, useEffect, useState } from "react"

import { deleteApiKey, loadApiKey, saveApiKey } from "~/lib/apikey-store"

export type ApiKeyStatus = "loading" | "missing" | "ready"

export interface UseApiKey {
  status: ApiKeyStatus
  key?: string
  /** Encrypt + store the key, then mark ready. */
  save: (key: string) => Promise<void>
  /** Remove the stored key, then mark missing. */
  clear: () => Promise<void>
}

/** Reads the encrypted API key from IndexedDB on mount and exposes save/clear. */
export function useApiKey(): UseApiKey {
  const [status, setStatus] = useState<ApiKeyStatus>("loading")
  const [key, setKey] = useState<string | undefined>(undefined)

  useEffect(() => {
    let active = true
    loadApiKey()
      .then((stored) => {
        if (!active) return
        if (stored) {
          setKey(stored)
          setStatus("ready")
        } else {
          setStatus("missing")
        }
      })
      .catch(() => {
        if (active) setStatus("missing")
      })
    return () => {
      active = false
    }
  }, [])

  const save = useCallback(async (newKey: string) => {
    await saveApiKey(newKey)
    setKey(newKey)
    setStatus("ready")
  }, [])

  const clear = useCallback(async () => {
    await deleteApiKey()
    setKey(undefined)
    setStatus("missing")
  }, [])

  return { status, key, save, clear }
}
