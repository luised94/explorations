/* api.js -- frontend HTTP seam (roadmap #1 modularization, E2).
 *
 * The JSON request helpers: readJson (response -> data, surfacing the backend's
 * {error} envelope as a thrown Error), and the apiGet / apiPost verbs built on
 * fetch. Verbatim relocation from the index.html inline script -- no behavior
 * change.
 *
 * SEAM BOUNDARY (E2 flag): two raw fetch() sites deliberately stay OUTSIDE this
 * seam because they are not plain JSON verbs --
 *   1. endSessionOnUnload's keepalive POST (sendBeacon fallback), which needs
 *      keepalive:true and fires during pagehide with no reader; and
 *   2. onImportSubmit's multipart POST (FormData, no Content-Type so the browser
 *      sets the boundary), which nonetheless parses its reply via readJson.
 * Both remain in their owning modules; the second imports readJson from here.
 * So readJson is a shared export, not private to the verbs.
 *
 * ADR-049 import-time rule: no DOM and no fetch at import time (fetch is only
 * called inside the async verbs). Import-safe under the option-(b) harness,
 * which stubs window.fetch before importing.
 *
 * Depends on nothing (leaf beside state.js). Per R1 (ADR-052) the inline script
 * keeps its own copy until the E10 cutover; nothing imports this until then.
 *
 * ASCII only.
 */

/* Read a JSON response, surfacing the backend's {error} envelope as a thrown
   Error so callers can show it in the interface's own voice. */
export async function readJson(response) {
  var data;
  try {
    data = await response.json();
  } catch (parseError) {
    throw new Error("The server sent a response that could not be read.");
  }
  if (!response.ok) {
    var message = (data && data.error) ? data.error
                                       : "Request failed (" + response.status + ").";
    throw new Error(message);
  }
  return data;
}

/* Run a fetch, translating a NETWORK failure (server gone: fetch rejects
   with a TypeError before any response exists) into a specific, actionable
   message. The browser's generic "Failed to fetch" told the human nothing
   when the serve terminal had been closed (use-period report); this names
   the one cause a local single-user tool realistically has. HTTP-level
   errors (a response arrived) are readJson's job, not this one's. */
async function fetchOrExplain(path, options) {
  try {
    return await fetch(path, options);
  } catch (networkError) {
    throw new Error(
      "Could not reach the drill server -- is 'uv run drill.py serve' "
      + "still running in its terminal?"
    );
  }
}

export async function apiGet(path) {
  var response = await fetchOrExplain(path, { headers: { "Accept": "application/json" } });
  return readJson(response);
}

export async function apiPost(path, body) {
  var response = await fetchOrExplain(path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Accept": "application/json"
    },
    body: JSON.stringify(body)
  });
  return readJson(response);
}
