import { Fragment } from "react"

import { cn } from "@/lib/utils"

/** ok = lilla; pending = ambra (serve attenzione); down = rosso (guasto); unknown = spenta. */
export type StationState = "ok" | "pending" | "down" | "unknown"

export type Station = {
  name: string
  state: StationState
  detail: string
}

const DASHED =
  "bg-[repeating-linear-gradient(180deg,var(--input)_0_6px,transparent_6px_10px)] md:bg-[repeating-linear-gradient(90deg,var(--input)_0_8px,transparent_8px_14px)]"

/**
 * Linea dei servizi: finché ogni fermata è operativa la linea corre intera.
 * Orizzontale da tablet in su; verticale su telefono, dove quattro etichette non stanno.
 */
export function ServiceLine({ stations }: { stations: Station[] }) {
  const last = stations.length - 1
  return (
    <ol
      aria-label="Servizi di Argo"
      className="flex flex-col pb-5 md:flex-row md:items-start md:pb-14"
    >
      {stations.map((station, index) => (
        <Fragment key={station.name}>
          {index > 0 && (
            <li
              aria-hidden
              className={cn(
                "ml-[7px] h-3 w-1 md:mt-[7px] md:ml-0 md:h-1 md:w-auto md:flex-1",
                station.state === "ok" && stations[index - 1].state === "ok"
                  ? "bg-line"
                  : DASHED
              )}
            />
          )}
          <li className="flex items-center gap-3 md:relative md:block md:size-[18px] md:shrink-0">
            <span
              aria-hidden
              className={cn(
                "block size-[18px] shrink-0 rounded-full border-[5px] bg-card",
                station.state === "ok" && "border-line",
                station.state === "pending" && "border-pending",
                station.state === "down" && "border-destructive",
                station.state === "unknown" && "border-input"
              )}
            />
            <span
              className={cn(
                "flex items-baseline gap-2 md:absolute md:top-7 md:w-max md:flex-col md:gap-0",
                index === 0 && "md:left-0",
                index === last &&
                  index > 0 &&
                  "md:right-0 md:items-end md:text-right",
                index !== 0 &&
                  index !== last &&
                  "md:left-1/2 md:-translate-x-1/2 md:items-center md:text-center"
              )}
            >
              <span className="text-sm leading-tight font-semibold">
                {station.name}
              </span>
              <span
                className={cn(
                  "text-[13px] leading-tight text-muted-foreground",
                  station.state === "pending" &&
                    "font-medium text-pending-foreground",
                  station.state === "down" && "font-medium text-destructive"
                )}
              >
                {station.detail}
              </span>
            </span>
          </li>
        </Fragment>
      ))}
    </ol>
  )
}
