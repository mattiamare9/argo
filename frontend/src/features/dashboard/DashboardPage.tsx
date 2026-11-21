import { AlertCircleIcon } from "lucide-react"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { useHealth } from "@/features/dashboard/api"

export function DashboardPage() {
  const health = useHealth()

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold">Dashboard</h1>
      <Card className="max-w-md">
        <CardHeader>
          <CardTitle>Stato del sistema</CardTitle>
          <CardDescription>Aggiornato ogni 30 secondi</CardDescription>
        </CardHeader>
        <CardContent>
          {health.isPending && <Skeleton className="h-12 w-full" />}
          {health.isError && (
            <Alert variant="destructive">
              <AlertCircleIcon />
              <AlertTitle>Backend non raggiungibile</AlertTitle>
              <AlertDescription>{health.error.message}</AlertDescription>
            </Alert>
          )}
          {health.isSuccess && (
            <dl className="grid grid-cols-[auto_1fr] items-center gap-x-6 gap-y-3 text-sm">
              <dt className="text-muted-foreground">API</dt>
              <dd>
                <StatusBadge ok />
              </dd>
              <dt className="text-muted-foreground">Database</dt>
              <dd>
                <StatusBadge ok={health.data.database === "ok"} />
              </dd>
            </dl>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function StatusBadge({ ok }: { ok: boolean }) {
  return (
    <Badge variant={ok ? "secondary" : "destructive"}>
      {ok ? "Operativo" : "Non raggiungibile"}
    </Badge>
  )
}
