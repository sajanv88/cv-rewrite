import { useState } from "react"
import { EyeIcon, EyeOffIcon, ShieldCheckIcon } from "lucide-react"

import { cn } from "~/lib/utils"
import { Alert, AlertDescription, AlertTitle } from "~/components/ui/alert"
import { Button } from "~/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "~/components/ui/dialog"
import { Input } from "~/components/ui/input"
import { Label } from "~/components/ui/label"

export type ApiKeyDialogMode = "first-time" | "change"

interface ApiKeyDialogProps {
  open: boolean
  mode: ApiKeyDialogMode
  onSave: (key: string) => Promise<void> | void
  /** Change mode only: called when the dialog wants to close. */
  onOpenChange?: (open: boolean) => void
  /** Change mode only: remove the stored key. */
  onClear?: () => void
  /** Whether a key is currently stored (controls the "Remove key" button). */
  hasKey?: boolean
}

export function ApiKeyDialog({
  open,
  mode,
  onSave,
  onOpenChange,
  onClear,
  hasKey,
}: ApiKeyDialogProps) {
  const [value, setValue] = useState("")
  const [show, setShow] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const firstTime = mode === "first-time"

  // First-time mode is non-dismissible: swallow every close request.
  function handleOpenChange(next: boolean) {
    if (firstTime) return
    onOpenChange?.(next)
  }

  async function handleSave() {
    const key = value.trim()
    if (!key.startsWith("sk-ant-")) {
      setError('That doesn\'t look right — an Anthropic key starts with "sk-ant-".')
      return
    }
    setError(null)
    setSaving(true)
    try {
      await onSave(key)
      setValue("")
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save the key.")
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent showCloseButton={!firstTime} className="max-w-lg">
        <DialogHeader>
          <DialogTitle>
            {firstTime ? "Add your Anthropic API key" : "Your Anthropic API key"}
          </DialogTitle>
          <DialogDescription>
            {firstTime
              ? "This app runs on your own Anthropic key. Add one to continue."
              : "Update or remove the key stored in this browser."}
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-2">
          <Label htmlFor="api-key-input">API key</Label>
          <div className="flex items-center gap-2">
            <Input
              id="api-key-input"
              type={show ? "text" : "password"}
              value={value}
              onChange={(e) => setValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleSave()
              }}
              placeholder="sk-ant-api03-…"
              className={cn("font-mono", error && "border-destructive")}
              autoComplete="off"
              autoCorrect="off"
              spellCheck={false}
              aria-invalid={error ? true : undefined}
            />
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              className="shrink-0"
              onClick={() => setShow((s) => !s)}
              aria-label={show ? "Hide key" : "Show key"}
            >
              {show ? <EyeOffIcon /> : <EyeIcon />}
            </Button>
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
        </div>

        <Alert className="border-emerald-500/30 bg-emerald-500/5">
          <ShieldCheckIcon className="text-emerald-600 dark:text-emerald-500" />
          <AlertTitle>Where your key goes</AlertTitle>
          <AlertDescription>
            It's encrypted with AES-256 and stored only in this browser
            (IndexedDB). It's sent with each request to this app's server, which
            uses it only to call Anthropic on your behalf — it is not stored or
            logged there.
          </AlertDescription>
        </Alert>

        <div className="flex flex-col gap-1.5 text-sm text-muted-foreground">
          <p className="font-medium text-foreground">How to get a key</p>
          <ol className="flex list-decimal flex-col gap-1 pl-5">
            <li>
              Go to{" "}
              <a
                href="https://console.anthropic.com"
                target="_blank"
                rel="noreferrer"
                className="underline underline-offset-2 hover:text-foreground"
              >
                console.anthropic.com
              </a>
            </li>
            <li>
              Open <span className="font-medium text-foreground">API Keys</span>
            </li>
            <li>
              Click <span className="font-medium text-foreground">Create Key</span>
            </li>
            <li>Copy it and paste it above</li>
          </ol>
          <p>
            A typical CV analysis costs a few cents — see{" "}
            <a
              href="https://www.anthropic.com/pricing"
              target="_blank"
              rel="noreferrer"
              className="underline underline-offset-2 hover:text-foreground"
            >
              anthropic.com/pricing
            </a>
            .
          </p>
        </div>

        <DialogFooter>
          {!firstTime && hasKey && onClear && (
            <Button variant="outline" onClick={onClear} className="sm:mr-auto">
              Remove key
            </Button>
          )}
          <Button onClick={handleSave} disabled={saving || value.trim().length === 0}>
            {saving ? "Saving…" : "Save key"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
