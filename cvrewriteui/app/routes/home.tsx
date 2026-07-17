import { useRef, useState } from "react"
import { toast } from "sonner"
import {
  FileTextIcon,
  SparklesIcon,
  UploadIcon,
  XIcon,
} from "lucide-react"

import type { Route } from "./+types/home"
import { rewriteCv, type RewriteResponse } from "~/lib/api"
import { cn } from "~/lib/utils"
import { Results } from "~/components/results"
import {
  Attachment,
  AttachmentActions,
  AttachmentAction,
  AttachmentContent,
  AttachmentDescription,
  AttachmentMedia,
  AttachmentTitle,
} from "~/components/ui/attachment"
import { Button } from "~/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "~/components/ui/card"
import { Field, FieldDescription, FieldLabel } from "~/components/ui/field"
import { Spinner } from "~/components/ui/spinner"
import { Textarea } from "~/components/ui/textarea"

export function meta(_: Route.MetaArgs) {
  return [
    { title: "CV Rewrite — honest, JD-tailored CVs" },
    {
      name: "description",
      content:
        "Upload your CV and a job description to get an honestly rewritten CV, a match score, and interview prep.",
    },
  ]
}

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)} KB`
  return `${(n / (1024 * 1024)).toFixed(1)} MB`
}

function Shell({
  children,
  wide = false,
}: {
  children: React.ReactNode
  wide?: boolean
}) {
  return (
    <main
      className={cn(
        "mx-auto flex min-h-dvh w-full flex-col gap-8 px-4 py-10 sm:py-16",
        wide ? "max-w-6xl" : "max-w-3xl",
      )}
    >
      <header className="flex flex-col gap-2 print:hidden">
        <div className="flex items-center gap-2">
          <SparklesIcon className="size-5 text-primary" />
          <h1 className="text-2xl font-semibold tracking-tight">CV Rewrite</h1>
        </div>
        <p className="text-sm text-muted-foreground">
          Upload your CV and the job description. We rewrite your CV for the role —
          without inventing anything — and give you an honest match score and
          interview prep.
        </p>
      </header>
      {children}
    </main>
  )
}

export default function Home() {
  const [file, setFile] = useState<File | null>(null)
  const [jd, setJd] = useState("")
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<RewriteResponse | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  function pickFile(f: File | null) {
    if (!f) return
    const isPdf =
      f.type === "application/pdf" || f.name.toLowerCase().endsWith(".pdf")
    if (!isPdf) {
      toast.error("Please choose a PDF file.")
      return
    }
    setFile(f)
  }

  async function submit() {
    if (!file) {
      toast.error("Upload your CV (PDF) first.")
      return
    }
    if (!jd.trim()) {
      toast.error("Paste the job description.")
      return
    }
    setLoading(true)
    try {
      const data = await rewriteCv(file, jd.trim())
      setResult(data)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Something went wrong.")
    } finally {
      setLoading(false)
    }
  }

  function reset() {
    setResult(null)
    setFile(null)
    setJd("")
  }

  if (result) {
    const twoColumn = Boolean(result.rewritten_cv && result.pdf_base64)
    return (
      <Shell wide={twoColumn}>
        <Results data={result} jobDescription={jd} onReset={reset} />
      </Shell>
    )
  }

  if (loading) {
    return (
      <Shell>
        <Card>
          <CardContent className="flex flex-col items-center gap-4 py-16 text-center">
            <Spinner className="size-8 text-primary" />
            <div className="flex flex-col gap-1">
              <p className="font-medium">Analyzing your CV against the role…</p>
              <p className="text-sm text-muted-foreground">
                Scoring the fit and rewriting your CV. This can take up to a minute.
              </p>
            </div>
          </CardContent>
        </Card>
      </Shell>
    )
  }

  return (
    <Shell>
      <Card>
        <CardHeader>
          <CardTitle>Get started</CardTitle>
          <CardDescription>
            Your CV is analyzed once and not stored.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-6">
          <Field>
            <FieldLabel htmlFor="cv-input">Your CV (PDF)</FieldLabel>
            <input
              ref={inputRef}
              id="cv-input"
              type="file"
              accept="application/pdf,.pdf"
              className="sr-only"
              onChange={(e) => pickFile(e.target.files?.[0] ?? null)}
            />
            {file ? (
              <Attachment orientation="horizontal" className="w-full">
                <AttachmentMedia>
                  <FileTextIcon />
                </AttachmentMedia>
                <AttachmentContent>
                  <AttachmentTitle>{file.name}</AttachmentTitle>
                  <AttachmentDescription>
                    {formatBytes(file.size)} · PDF
                  </AttachmentDescription>
                </AttachmentContent>
                <AttachmentActions>
                  <AttachmentAction
                    aria-label="Remove file"
                    onClick={() => {
                      setFile(null)
                      if (inputRef.current) inputRef.current.value = ""
                    }}
                  >
                    <XIcon />
                  </AttachmentAction>
                </AttachmentActions>
              </Attachment>
            ) : (
              <button
                type="button"
                onClick={() => inputRef.current?.click()}
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault()
                  pickFile(e.dataTransfer.files?.[0] ?? null)
                }}
                className="flex flex-col items-center gap-2 rounded-2xl border border-dashed bg-input/30 px-4 py-10 text-center transition-colors hover:bg-input/50 focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/30 focus-visible:outline-none"
              >
                <UploadIcon className="size-6 text-muted-foreground" />
                <span className="text-sm font-medium">
                  Click to upload or drag &amp; drop
                </span>
                <span className="text-xs text-muted-foreground">PDF, up to 20 MB</span>
              </button>
            )}
          </Field>

          <Field>
            <FieldLabel htmlFor="jd-input">Job description</FieldLabel>
            <Textarea
              id="jd-input"
              value={jd}
              onChange={(e) => setJd(e.target.value)}
              placeholder="Paste the full job description here…"
              className="min-h-40"
            />
            <FieldDescription>
              The more complete the JD, the more accurate the score and rewrite.
            </FieldDescription>
          </Field>

          <Button size="lg" className="w-full" onClick={submit}>
            <SparklesIcon />
            Rewrite my CV
          </Button>
        </CardContent>
      </Card>
    </Shell>
  )
}
