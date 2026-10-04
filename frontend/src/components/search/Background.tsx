// The grid paper itself comes from the app shell (pi-grid). On top of it, two very
// faint pools of blue light drift slowly, like a lamp over a drafting table.
// Radial gradients (no blur filter) moved by a transform-only keyframe.
// The layer sticks to the top of the scroll area and takes no space in the flow.
export function Background({ calm = false }: { calm?: boolean }) {
  return (
    <div aria-hidden className="pointer-events-none sticky top-0 -z-10 -mb-[100vh] h-screen overflow-hidden">
      <div className={`absolute inset-0 transition-opacity duration-1000 ${calm ? "opacity-40" : "opacity-100"}`}>
        <div className="blob" style={{ width: "48vw", height: "48vw", left: "-12vw", top: "-18vw", background: "radial-gradient(closest-side, var(--glow), transparent)" }} />
        <div
          className="blob"
          style={{ width: "40vw", height: "40vw", right: "-10vw", bottom: "-14vw", animationDelay: "-14s", animationDuration: "36s", background: "radial-gradient(closest-side, var(--glow), transparent)" }}
        />
      </div>
    </div>
  );
}
