import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "./client";

afterEach(() => {
  vi.restoreAllMocks();
});

function mockFetch(body: unknown, ok = true, status = 200) {
  return vi.fn().mockResolvedValue({
    ok,
    status,
    json: () => Promise.resolve(body),
  } as Response);
}

describe("api client", () => {
  it("buduje URL z bazą i zwraca sparsowane JSON", async () => {
    const fetchMock = mockFetch({ total_games: 5 });
    vi.stubGlobal("fetch", fetchMock);

    const result = await api.overview();

    expect(fetchMock).toHaveBeenCalledOnce();
    const calledUrl = fetchMock.mock.calls[0][0] as string;
    expect(calledUrl).toContain("/api/overview");
    expect(result.total_games).toBe(5);
  });

  it("dokleja parametry zapytania do /api/games", async () => {
    const fetchMock = mockFetch({ items: [], total: 0 });
    vi.stubGlobal("fetch", fetchMock);

    await api.games({ q: "half", limit: 10 });

    const calledUrl = fetchMock.mock.calls[0][0] as string;
    expect(calledUrl).toContain("/api/games");
    expect(calledUrl).toContain("q=half");
    expect(calledUrl).toContain("limit=10");
  });

  it("rzuca błąd przy odpowiedzi nie-ok", async () => {
    vi.stubGlobal("fetch", mockFetch({ detail: "nope" }, false, 404));
    await expect(api.gameDetail(1)).rejects.toThrow();
  });
});
