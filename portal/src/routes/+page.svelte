<script>
  import { onMount } from 'svelte';
  import { loadAll } from '$lib/api.js';

  let data = $state({ players: [], teams: [], matches: [], standings: [] });
  let loading = $state(true);

  onMount(async () => {
    try { data = await loadAll(); } catch(e) { console.error(e); }
    loading = false;
  });

  const ROUND_ORDER = ['Round of 16','Quarterfinal','Semifinal','3rd Place','Grand Final'];

  function matchesByRound() {
    const map = new Map();
    for (const m of data.matches) {
      if (!map.has(m.round)) map.set(m.round, []);
      map.get(m.round).push(m);
    }
    return map;
  }

  function statusIcon(s) {
    return { scheduled:'⏳', in_progress:'🔴', completed:'✅', pending:'⏸️', bye:'↪️' }[s] || '❓';
  }
</script>

<svelte:head><title>Bracket — Vava Bot4Bots Cup</title></svelte:head>

<div>
  <h2 class="text-val-red fw-bold mb-4">Tournament Bracket</h2>

  {#if loading}
    <p class="text-secondary">Loading...</p>
  {:else if data.matches.length === 0}
    <div class="card p-4 text-center text-secondary">
      <p class="mb-0 fs-5">Bracket not generated yet</p>
      <small>Check back once teams are formed!</small>
    </div>
  {:else}
    <div class="d-flex gap-4 overflow-auto pb-3">
      {#each ROUND_ORDER.filter(r => matchesByRound().has(r)) as round}
        <div style="min-width: 250px">
          <h6 class="text-val-red text-uppercase fw-bold mb-2 small">{round}</h6>
          {#each matchesByRound().get(round) as m}
            <div class="match-card p-3 mb-2 {m.status === 'bye' ? 'bye' : ''} {m.status === 'completed' ? 'completed' : ''}">
              <div class="text-secondary mb-1" style="font-size:0.7rem">{statusIcon(m.status)} Match #{m.id}</div>
              <div class="small fw-semibold {m.status === 'completed' && m.winner_id === m.team1.id ? 'winner-text' : ''}">
                {m.team1.name}
              </div>
              <div class="text-center text-secondary py-1" style="font-size:0.65rem">VS</div>
              <div class="small fw-semibold {m.status === 'completed' && m.winner_id === m.team2.id ? 'winner-text' : ''}">
                {m.team2.name}
              </div>
              {#if m.score}
                <div class="text-center fw-bold text-val-gold mt-1 small">{m.score[0]} — {m.score[1]}</div>
              {/if}
              <div class="text-center text-secondary mt-1" style="font-size:0.65rem">
                {m.scheduled_date}<br/>{m.scheduled_time || 'TBD'}
              </div>
            </div>
          {/each}
        </div>
      {/each}
    </div>

    {#if data.standings.length > 0}
      <h4 class="text-val-red fw-bold mt-5 mb-3">Standings</h4>
      <div class="card overflow-hidden">
        <table class="table table-borderless mb-0 small">
          <thead>
            <tr><th>#</th><th>Team</th><th>W</th><th>L</th><th>Maps</th></tr>
          </thead>
          <tbody>
            {#each data.standings as t, i}
              <tr>
                <td class="text-val-red fw-bold">{i+1}</td>
                <td>{t.name}</td>
                <td class="text-success">{t.wins}</td>
                <td class="text-danger">{t.losses}</td>
                <td class="text-val-gold small">{t.maps_won}-{t.maps_lost}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  {/if}
</div>
