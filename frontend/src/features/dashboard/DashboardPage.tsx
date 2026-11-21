import { Skeleton } from "@/components/ui/skeleton"
import { AttentionList } from "@/features/dashboard/AttentionList"
import { KeyBoard } from "@/features/dashboard/KeyBoard"
import { ServiceLine } from "@/features/dashboard/ServiceLine"
import {
  useBoard,
  useHealth,
  useRuns,
  useSyncOverview,
} from "@/features/dashboard/api"
import { systemStatus } from "@/features/dashboard/status"

export function DashboardPage() {
  const health = useHealth()
  const overview = useSyncOverview()
  const openRuns = useRuns(true)
  const board = useBoard()

  const loading = health.isPending || overview.isPending || openRuns.isPending
  const status = systemStatus({
    apiDown: health.isError,
    dbDown: health.data?.database === "unreachable",
    overview: overview.data,
    openRuns: openRuns.data,
    now: overview.dataUpdatedAt,
  })

  return (
    <div className="flex flex-col">
      <section className="border-b bg-card px-4 pt-5 md:px-12">
        {loading ? (
          <Skeleton className="mb-5 h-12 w-full" />
        ) : (
          <ServiceLine stations={status.stations} />
        )}
      </section>

      <section className="flex flex-col gap-3 px-4 pt-8 pb-8 md:px-12 md:pt-14">
        {loading ? (
          <Skeleton className="h-14 w-full max-w-lg" />
        ) : (
          <>
            <h1 className="text-4xl font-bold tracking-[-0.03em] text-balance md:text-6xl">
              {status.headline}
            </h1>
            <p className="max-w-[60ch] text-base text-muted-foreground md:text-lg">
              {status.detail}
            </p>
          </>
        )}
      </section>

      <div className="flex flex-col gap-10 px-4 pb-12 md:px-12">
        <AttentionList
          pending={overview.data?.pending ?? null}
          partialRuns={(openRuns.data ?? []).filter(
            (run) => run.status === "partial"
          )}
        />
        <section aria-labelledby="quadro">
          <h2 id="quadro" className="mb-4 text-base font-semibold">
            Quadro accessi
          </h2>
          {board.isPending ? (
            <Skeleton className="h-40 w-full" />
          ) : board.isError ? (
            <p role="alert" className="text-destructive">
              Il quadro non si è caricato: {board.error.message}
            </p>
          ) : (
            <KeyBoard plates={board.data ?? []} />
          )}
        </section>
      </div>
    </div>
  )
}
