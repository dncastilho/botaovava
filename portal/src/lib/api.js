const API = '/api';

export async function fetchJson(path) {
  const res = await fetch(`${API}${path}`);
  if (!res.ok) throw new Error(`API ${path} failed`);
  return res.json();
}

export async function loadPlayers() { return fetchJson('/players'); }
export async function loadTeams() { return fetchJson('/teams'); }
export async function loadMatches() { return fetchJson('/matches'); }
export async function loadStandings() { return fetchJson('/standings'); }
export async function loadAll() {
  const [players, teams, matches, standings] = await Promise.all([
    loadPlayers(), loadTeams(), loadMatches(), loadStandings()
  ]);
  return { players, teams, matches, standings };
}
