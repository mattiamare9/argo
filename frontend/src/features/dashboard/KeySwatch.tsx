import { cn } from "@/lib/utils"

export type KeyState = "hung" | "returned" | "pending"

/** La chiave del quadro: appesa (accesso attivo), riconsegnata, o in attesa di riconsegna. */
export function KeySwatch({ state }: { state: KeyState }) {
  return (
    <span
      aria-hidden
      className={cn(
        "inline-block h-5 w-3 shrink-0 rounded-t-full rounded-b-[3px]",
        state === "hung" && "bg-line",
        state === "returned" &&
          "border-2 border-dashed border-muted-foreground",
        state === "pending" && "border-2 border-pending bg-pending-soft"
      )}
    />
  )
}
