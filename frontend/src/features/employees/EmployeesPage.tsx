import { keepPreviousData, useQuery } from "@tanstack/react-query"
import { SearchIcon } from "lucide-react"
import { useDeferredValue, useState } from "react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { apiGet } from "@/lib/api"
import { cn } from "@/lib/utils"

type Employee = {
  id: string
  employee_id: string
  email: string
  first_name: string
  last_name: string
  status: "ACTIVE" | "INACTIVE"
  status_changed_at: string
}

type EmployeePage = {
  items: Employee[]
  total: number
  page: number
  page_size: number
}

type Filter = "all" | "ACTIVE" | "INACTIVE"

const PAGE_SIZE = 25
const date = new Intl.DateTimeFormat("it-IT", { dateStyle: "medium" })

function useEmployees(search: string, filter: Filter, page: number) {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(PAGE_SIZE),
  })
  if (search) params.set("search", search)
  if (filter !== "all") params.set("status", filter)
  return useQuery({
    queryKey: ["employees", search, filter, page],
    queryFn: () => apiGet<EmployeePage>(`/api/employees?${params}`),
    placeholderData: keepPreviousData,
  })
}

export function EmployeesPage() {
  const [search, setSearch] = useState("")
  const [filter, setFilter] = useState<Filter>("all")
  const [page, setPage] = useState(1)
  const deferredSearch = useDeferredValue(search.trim())
  const employees = useEmployees(deferredSearch, filter, page)
  const pages = employees.data
    ? Math.max(1, Math.ceil(employees.data.total / PAGE_SIZE))
    : 1

  return (
    <div className="flex flex-col gap-6 px-4 py-8 md:px-12 md:py-14">
      <div className="flex flex-col gap-2">
        <h1 className="text-4xl font-bold tracking-[-0.03em]">Dipendenti</h1>
        <p className="max-w-[60ch] text-muted-foreground">
          Come risultano dal file dei dipendenti. Si modificano solo lì: Argo
          legge il file e aggiorna gli accessi.
        </p>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative sm:w-80">
          <SearchIcon
            aria-hidden
            className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground"
          />
          <Input
            aria-label="Cerca per nome, email o codice"
            placeholder="Cerca per nome, email o codice"
            className="pl-8"
            value={search}
            onChange={(event) => {
              setSearch(event.target.value)
              setPage(1)
            }}
          />
        </div>
        <ToggleGroup
          aria-label="Filtra per stato"
          variant="outline"
          value={[filter]}
          onValueChange={(value) => {
            if (value[0]) setFilter(value[0] as Filter)
            setPage(1)
          }}
        >
          <ToggleGroupItem value="all">Tutti</ToggleGroupItem>
          <ToggleGroupItem value="ACTIVE">Attivi</ToggleGroupItem>
          <ToggleGroupItem value="INACTIVE">Non attivi</ToggleGroupItem>
        </ToggleGroup>
      </div>

      {employees.isPending ? (
        <Skeleton className="h-64 w-full" />
      ) : employees.isError ? (
        <p role="alert" className="text-destructive">
          {employees.error.message}
        </p>
      ) : employees.data.items.length === 0 ? (
        <p className="text-muted-foreground">
          {deferredSearch || filter !== "all"
            ? "Nessun dipendente corrisponde alla ricerca."
            : "Nessun dipendente: compariranno alla prima lettura del file."}
        </p>
      ) : (
        <div className="overflow-x-auto rounded-lg border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Codice</TableHead>
                <TableHead>Nome</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Stato</TableHead>
                <TableHead>Dal</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {employees.data.items.map((e) => (
                <TableRow key={e.id}>
                  <TableCell className="tabular-nums">
                    {e.employee_id}
                  </TableCell>
                  <TableCell className="font-medium">
                    {e.first_name} {e.last_name}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {e.email}
                  </TableCell>
                  <TableCell>
                    <span className="flex items-center gap-2">
                      <span
                        aria-hidden
                        className={cn(
                          "size-2 rounded-full",
                          e.status === "ACTIVE" ? "bg-line" : "bg-input"
                        )}
                      />
                      {e.status === "ACTIVE" ? "Attivo" : "Non attivo"}
                    </span>
                  </TableCell>
                  <TableCell className="text-muted-foreground tabular-nums">
                    {date.format(Date.parse(e.status_changed_at))}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {employees.data && pages > 1 && (
        <nav
          aria-label="Pagine"
          className="flex items-center justify-between gap-4 text-sm"
        >
          <span className="text-muted-foreground">
            {employees.data.total} dipendenti · pagina {page} di {pages}
          </span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage(page - 1)}
            >
              Precedente
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= pages}
              onClick={() => setPage(page + 1)}
            >
              Successiva
            </Button>
          </div>
        </nav>
      )}
    </div>
  )
}
