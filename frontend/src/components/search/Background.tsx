// Soft colour blobs drifting slowly behind the page. Radial gradients instead of a
// CSS blur filter (much cheaper to paint); the drift is a transform-only keyframe.
// The layer sticks to the top of the scroll area and takes no space in the flow.
export function Background({ calm = false }: { calm?: boolean }) {
  return (
    <div aria-hidden className="pointer-events-none sticky top-0 -mb-[100vh] h-screen overflow-hidden">
      <div className={`absolute inset-0 transition-opacity duration-1000 ${calm ? "opacity-45" : "opacity-100"}`}>
        <div
          className="blob blob-a"
          style={{ width: "46vw", height: "46vw", left: "-10vw", top: "-14vw", background: "radial-gradient(closest-side, rgb(217 119 87 / 0.26), transparent)" }}
        />
        <div
          className="blob blob-b"
          style={{ width: "40vw", height: "40vw", right: "-8vw", top: "4vh", background: "radial-gradient(closest-side, rgb(106 155 204 / 0.2), transparent)" }}
        />
        <div
          className="blob blob-c"
          style={{ width: "42vw", height: "42vw", left: "28vw", bottom: "-18vw", background: "radial-gradient(closest-side, rgb(156 175 136 / 0.24), transparent)" }}
        />
      </div>
    </div>
  );
}
