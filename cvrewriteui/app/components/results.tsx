import { useState } from "react"
import { toast } from "sonner"
import {
  BuildingIcon,
  CircleCheckIcon,
  DownloadIcon,
  FileTextIcon,
  GraduationCapIcon,
  LightbulbIcon,
  MessageSquareIcon,
  PrinterIcon,
  RotateCcwIcon,
  TargetIcon,
  TriangleAlertIcon,
} from "lucide-react"

import type { RewriteResponse, Verdict } from "~/lib/api"
import { buildInterviewGuide, downloadPdf, pdfDataUrl } from "~/lib/api"
import { cn } from "~/lib/utils"
import { Alert, AlertDescription, AlertTitle } from "~/components/ui/alert"
import { Badge } from "~/components/ui/badge"
import { Button } from "~/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "~/components/ui/card"
import { Progress } from "~/components/ui/progress"
import { Separator } from "~/components/ui/separator"
import { Spinner } from "~/components/ui/spinner"

const VERDICT: Record<
  Verdict,
  { label: string; badge: "default" | "secondary" | "outline" | "destructive" }
> = {
  STRONG: { label: "Strong match", badge: "default" },
  PARTIAL: { label: "Partial match", badge: "secondary" },
  WEAK: { label: "Weak match", badge: "outline" },
  NOT_RECOMMENDED: { label: "Not recommended", badge: "destructive" },
}

function scoreTone(score: number): string {
  if (score >= 80) return "text-primary"
  if (score >= 60) return "text-foreground"
  if (score >= 40) return "text-amber-600 dark:text-amber-500"
  return "text-destructive"
}

function SectionTitle({
  icon: Icon,
  children,
}: {
  icon: React.ComponentType<{ className?: string }>
  children: React.ReactNode
}) {
  return (
    <div className="flex items-center gap-2">
      <Icon className="size-4 text-muted-foreground" />
      <CardTitle>{children}</CardTitle>
    </div>
  )
}

function BulletList({
  items,
  icon: Icon,
  tone,
}: {
  items: string[]
  icon: React.ComponentType<{ className?: string }>
  tone: string
}) {
  return (
    <ul className="flex flex-col gap-2">
      {items.map((item, i) => (
        <li key={i} className="flex gap-2 text-sm">
          <Icon className={cn("mt-0.5 size-4 shrink-0", tone)} />
          <span className="leading-snug">{item}</span>
        </li>
      ))}
    </ul>
  )
}

export function Results({
  data,
  jobDescription,
  onReset,
}: {
  data: RewriteResponse
  jobDescription: string
  onReset: () => void
}) {
  const { score_report: report, rewritten_cv: cv, interview_prep: prep } = data
  const verdict = VERDICT[report.verdict]
  const hasCv = Boolean(cv && data.pdf_base64)
  const rewriteNote = cv?.rewrite_note?.trim() ?? ""
  const [guideLoading, setGuideLoading] = useState(false)

  async function buildGuide() {
    setGuideLoading(true)
    try {
      const guide = await buildInterviewGuide(jobDescription, data)
      downloadPdf(guide.pdf_base64, guide.pdf_filename)
      toast.success("Your interview prep guide is ready — downloading now.")
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not build the guide.")
    } finally {
      setGuideLoading(false)
    }
  }

  // --- The review: score report -------------------------------------------- //
  const scoreCard = (
    <Card className="min-w-0 print:shadow-none print:ring-0 print:[print-color-adjust:exact] print:[-webkit-print-color-adjust:exact]">
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex flex-col gap-1">
            <CardTitle>Match Score Report</CardTitle>
            <Badge variant={verdict.badge} className="w-fit">
              {verdict.label}
            </Badge>
          </div>
          <div
            className={cn(
              "text-4xl font-semibold tabular-nums",
              scoreTone(report.overall_score),
            )}
          >
            {report.overall_score}
            <span className="text-lg text-muted-foreground">/100</span>
          </div>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        <Progress value={report.overall_score} />

        <div className="grid gap-3 sm:grid-cols-2">
          {report.dimensions.map((d, i) => (
            <div key={i} className="flex flex-col gap-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="font-medium">{d.name}</span>
                <span className="text-muted-foreground tabular-nums">
                  {d.score.toFixed(1)}/10 · {d.weight}%
                </span>
              </div>
              <Progress
                value={d.score}
                max={10}
                className="**:data-[slot=progress-track]:h-1.5"
              />
            </div>
          ))}
        </div>

        {(report.why_apply.length > 0 || report.why_think_twice.length > 0) && (
          <>
            <Separator />
            <div className="grid gap-6 sm:grid-cols-2">
              {report.why_apply.length > 0 && (
                <div className="flex flex-col gap-2">
                  <h3 className="text-sm font-medium">Why you should apply</h3>
                  <BulletList
                    items={report.why_apply}
                    icon={CircleCheckIcon}
                    tone="text-primary"
                  />
                </div>
              )}
              {report.why_think_twice.length > 0 && (
                <div className="flex flex-col gap-2">
                  <h3 className="text-sm font-medium">
                    Why you should think twice
                  </h3>
                  <BulletList
                    items={report.why_think_twice}
                    icon={TriangleAlertIcon}
                    tone="text-amber-600 dark:text-amber-500"
                  />
                </div>
              )}
            </div>
          </>
        )}

        {report.gaps.length > 0 && (
          <>
            <Separator />
            <div className="flex flex-col gap-3">
              <h3 className="text-sm font-medium">Gaps identified</h3>
              <div className="flex flex-col gap-3">
                {report.gaps.map((g, i) => (
                  <div key={i} className="rounded-2xl border p-3 text-sm">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-medium">{g.requirement}</span>
                      <Badge variant={g.closable ? "secondary" : "destructive"}>
                        {g.closable ? "Closable" : "Hard gap"}
                      </Badge>
                    </div>
                    <p className="mt-1 text-muted-foreground">
                      You have: {g.candidate_has}
                    </p>
                    {g.closable && g.how_to_close && (
                      <p className="mt-1">How to close: {g.how_to_close}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </>
        )}

        {report.ats_flags.length > 0 && (
          <>
            <Separator />
            <div className="flex flex-col gap-2">
              <h3 className="text-sm font-medium">ATS risk flags</h3>
              <BulletList
                items={report.ats_flags}
                icon={TriangleAlertIcon}
                tone="text-muted-foreground"
              />
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )

  // --- The review: interview prep ------------------------------------------ //
  const prepCard = prep ? (
    <Card className="min-w-0 print:hidden">
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <SectionTitle icon={MessageSquareIcon}>
            Interview Preparation
          </SectionTitle>
          <Button
            size="sm"
            variant="outline"
            onClick={buildGuide}
            disabled={guideLoading}
          >
            {guideLoading ? (
              <Spinner className="size-4" />
            ) : (
              <GraduationCapIcon />
            )}
            {guideLoading ? "Building guide…" : "Build prep guide (PDF)"}
          </Button>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        {prep.likely_questions.length > 0 && (
          <div className="flex flex-col gap-2">
            <h3 className="text-sm font-medium">Likely questions</h3>
            <ol className="flex list-decimal flex-col gap-1.5 pl-5 text-sm">
              {prep.likely_questions.map((q, i) => (
                <li key={i}>{q}</li>
              ))}
            </ol>
          </div>
        )}
        {prep.talking_points.length > 0 && (
          <div className="flex flex-col gap-2">
            <h3 className="text-sm font-medium">Your strongest talking points</h3>
            <BulletList
              items={prep.talking_points}
              icon={TargetIcon}
              tone="text-primary"
            />
          </div>
        )}
        {prep.topics_to_prepare.length > 0 && (
          <div className="flex flex-col gap-2">
            <h3 className="text-sm font-medium">Topics to prepare</h3>
            <BulletList
              items={prep.topics_to_prepare}
              icon={LightbulbIcon}
              tone="text-amber-600 dark:text-amber-500"
            />
          </div>
        )}
        {prep.company_research && (
          <div className="flex flex-col gap-2">
            <SectionTitle icon={BuildingIcon}>Company research</SectionTitle>
            <p className="whitespace-pre-line text-sm leading-relaxed text-muted-foreground">
              {prep.company_research}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  ) : null

  // --- The rewritten CV — full-width, so the A4 page has room to breathe --- //
  const cvCard =
    hasCv && cv ? (
      <Card className="print:hidden">
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <SectionTitle icon={FileTextIcon}>Rewritten CV</SectionTitle>
            <Button
              onClick={() =>
                downloadPdf(data.pdf_base64!, data.pdf_filename ?? "CV.pdf")
              }
            >
              <DownloadIcon />
              Download PDF
            </Button>
          </div>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <iframe
            title="Rewritten CV preview"
            src={pdfDataUrl(data.pdf_base64!)}
            className="h-[85vh] min-h-150 w-full rounded-2xl border bg-muted"
          />
        </CardContent>
      </Card>
    ) : null

  return (
    <div className="flex flex-col gap-6">
      {/* Top action bar (hidden when printing) */}
      <div className="flex flex-wrap items-center gap-2 print:hidden">
        {hasCv && (
          <Button
            onClick={() =>
              downloadPdf(data.pdf_base64!, data.pdf_filename ?? "CV.pdf")
            }
          >
            <DownloadIcon />
            Download CV
          </Button>
        )}
        <Button variant="outline" onClick={() => window.print()}>
          <PrinterIcon />
          Print match score report
        </Button>
      </div>

      {/* Coaching note about the rewrite — shown here, never printed into the CV. */}
      {rewriteNote && (
        <Alert className="border-amber-500/30 bg-amber-500/5 print:hidden">
          <TriangleAlertIcon className="text-amber-600 dark:text-amber-500" />
          <AlertTitle>About your rewritten CV</AlertTitle>
          <AlertDescription className="whitespace-pre-line">
            {rewriteNote}
          </AlertDescription>
        </Alert>
      )}

      {/* Review — two columns on wide screens (score report + interview prep).
          On print, only the score report survives (prep is print:hidden). */}
      {prepCard ? (
        <div className="grid items-start gap-6 lg:grid-cols-2 print:grid-cols-1">
          {scoreCard}
          {prepCard}
        </div>
      ) : (
        scoreCard
      )}

      {/* Rewritten CV — its own full-width section */}
      {cvCard}

      <div className="flex justify-center print:hidden">
        <Button variant="outline" onClick={onReset}>
          <RotateCcwIcon />
          Rewrite another CV
        </Button>
      </div>
    </div>
  )
}
