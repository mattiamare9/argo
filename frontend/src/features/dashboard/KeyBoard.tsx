import { KeySwatch, type KeyState } from "@/features/dashboard/KeySwatch"
import type { Plate } from "@/features/dashboard/api"
import { cn } from "@/lib/utils"

const LEGEND: { state: KeyState; label: string }[] = [
  { state: "hung", label: "Chiave appesa: accesso attivo" },
  { state: "returned", label: "Gancio vuoto: accesso riconsegnato" },
  { state: "pending", label: "Chiave in ambra: operazione non completata" },
]

const KEY_STATE_LABEL: Record<KeyState, string> = {
  hung: "attivo",
  returned: "riconsegnato",
  pending: "operazione non completata",
}

/** Il quadro accessi: una targhetta per persona, una chiave per accesso gestito da Argo. */
export function KeyBoard({ plates }: { plates: Plate[] }) {
  return (
    <div className="flex flex-col gap-6 rounded-xl bg-muted p-4 shadow-[inset_0_2px_6px_rgb(74_54_120/0.08)] md:p-8">
      {plates.length === 0 ? (
        <div className="flex max-w-[60ch] flex-col gap-1.5">
          <p className="font-semibold">Il quadro è ancora vuoto</p>
          <p className="text-muted-foreground">
            Ogni dipendente comparirà qui con le chiavi delle applicazioni a cui
            ha accesso, alla prima lettura del file dei dipendenti.
          </p>
        </div>
      ) : (
        <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6">
          {plates.map((plate) => (
            <li
              key={plate.employee_id}
              className={cn(
                "flex flex-col gap-3 rounded-lg border bg-card p-3",
                plate.keys.some((k) => k.state === "pending") &&
                  "border-pending"
              )}
            >
              <div className="flex items-baseline justify-between gap-2 text-xs text-muted-foreground">
                <data value={plate.employee_id}>{plate.employee_id}</data>
                {plate.status === "INACTIVE" && <span>non attivo</span>}
              </div>
              <span
                className={cn(
                  "truncate text-sm font-semibold",
                  plate.status === "INACTIVE" && "text-muted-foreground"
                )}
              >
                {plate.first_name} {plate.last_name}
              </span>
              <ul className="flex gap-1.5" aria-label="Accessi">
                {plate.keys.map((key) => (
                  <li
                    key={key.name}
                    title={`${key.name}: ${KEY_STATE_LABEL[key.state]}`}
                  >
                    <KeySwatch state={key.state} />
                    <span className="sr-only">
                      {key.name}: {KEY_STATE_LABEL[key.state]}
                    </span>
                  </li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
      )}
      <ul
        aria-label="Legenda"
        className="flex flex-col gap-3 border-t border-input pt-5 text-sm md:flex-row md:gap-8"
      >
        {LEGEND.map((item) => (
          <li key={item.state} className="flex items-center gap-2.5">
            <KeySwatch state={item.state} />
            {item.label}
          </li>
        ))}
      </ul>
    </div>
  )
}
