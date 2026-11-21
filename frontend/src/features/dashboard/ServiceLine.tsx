import { Fragment } from "react"

import { cn } from "@/lib/utils"

export type StationState = "ok" | "down" | "unknown"

export type Station = {
  name: string
  state: StationState
  detail: string
}

const STATE_LABEL: Record<StationState, string> = {
  ok: "operativo",
  down: "non risponde",
  unknown: "non verificabile",
}

/** Linea dei servizi: finché ogni fermata è operativa la linea corre intera. */
export function ServiceLine({ stations }: { stations: Station[] }) {
  const last = stations.length - 1
  return (
    <ol aria-label="Servizi di Argo" className="flex items-start pb-14">
      {stations.map((station, index) => (
        <Fragment key={station.name}>
          {index > 0 && (
            <li
              aria-hidden
              className={cn(
                "mt-[7px] h-1 flex-1",
                station.state === "ok" && stations[index - 1].state === "ok"
                  ? "bg-line"
                  : "bg-[repeating-linear-gradient(90deg,var(--input)_0_8px,transparent_8px_14px)]"
              )}
            />
          )}
          <li className="relative size-[18px] shrink-0">
            <span
              aria-hidden
              className={cn(
                "block size-full rounded-full border-[5px] bg-card",
                station.state === "ok" && "border-line",
                station.state === "down" && "border-destructive",
                station.state === "unknown" && "border-input"
              )}
            />
            <span
              className={cn(
                "absolute top-7 flex flex-col whitespace-nowrap",
                index === 0 && "left-0",
                index === last && index > 0 && "right-0 items-end text-right",
                index !== 0 &&
                  index !== last &&
                  "left-1/2 -translate-x-1/2 items-center text-center"
              )}
            >
              <span className="text-sm font-semibold">{station.name}</span>
              <span
                className={cn(
                  "text-[13px] text-muted-foreground",
                  station.state === "down" && "font-medium text-destructive"
                )}
              >
                {station.state === "ok"
                  ? station.detail
                  : STATE_LABEL[station.state]}
              </span>
            </span>
          </li>
        </Fragment>
      ))}
    </ol>
  )
}
