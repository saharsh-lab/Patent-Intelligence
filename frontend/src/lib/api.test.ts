import { describe, expect, it } from "vitest";

import { parseError } from "./api";

describe("parseError", () => {
  it("reads the backend's standard error body", async () => {
    const response = new Response(
      JSON.stringify({ error: { code: "file_too_large", message: "File exceeds the 25 MB limit.", request_id: "abc" } }),
      { status: 413 },
    );
    const error = await parseError(response);
    expect(error).toMatchObject({ status: 413, code: "file_too_large", message: "File exceeds the 25 MB limit.", requestId: "abc" });
  });

  it("explains proxy failures when the backend is down", async () => {
    const error = await parseError(new Response("<html>Internal Server Error</html>", { status: 500 }));
    expect(error.message).toMatch(/backend running/);
  });
});
