import { PageHeader, Panel } from "@/components/ui";

/** Honest placeholder for features scheduled in later project phases. */
export function PlannedFeature({
  title,
  phase,
  summary,
  bullets,
}: {
  title: string;
  phase: number;
  summary: string;
  bullets: string[];
}) {
  return (
    <>
      <PageHeader title={title} description={summary} />
      <Panel title={`Planned for Phase ${phase}`}>
        <p className="text-sm text-muted">This feature is designed but not yet built. It will:</p>
        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
          {bullets.map((b) => (
            <li key={b}>{b}</li>
          ))}
        </ul>
      </Panel>
    </>
  );
}
