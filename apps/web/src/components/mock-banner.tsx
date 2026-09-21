import type { MetaRead } from '@/lib/api/generated'

export function MockBanner({ meta }: { meta: MetaRead | undefined }) {
  if (meta?.circuit === 'open') {
    return (
      <div
        role="alert"
        className="rounded-lg border border-red-300 bg-red-50 px-4 py-2 text-sm text-red-900 dark:border-red-700 dark:bg-red-950/40 dark:text-red-100"
      >
        <strong>Jev unavailable.</strong> Triage is paused after repeated failures. Moves into
        Triaged are rejected until the provider answers again.
      </div>
    )
  }
  if (!meta?.mock) return null
  return (
    <div
      role="status"
      className="rounded-lg border border-amber-300 bg-amber-50 px-4 py-2 text-sm text-amber-900 dark:border-amber-700 dark:bg-amber-950/40 dark:text-amber-100"
    >
      <strong>Mock triage: no AI key configured.</strong> Results come from keyword heuristics,
      not Jev. Set <code>TYPESAFE_API_KEY</code> in <code>apps/api/.env</code> to use the real
      model.
    </div>
  )
}
