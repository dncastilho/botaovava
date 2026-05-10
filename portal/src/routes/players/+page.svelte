<script>
  import { onMount } from 'svelte';
  import { loadPlayers } from '$lib/api.js';

  let players = $state([]);
  let loading = $state(true);

  onMount(async () => {
    try { players = await loadPlayers(); } catch(e) { console.error(e); }
    loading = false;
  });

  let sorted = $derived([...players].sort((a,b) => (a.discord_display||'').localeCompare(b.discord_display||'')));
</script>

<svelte:head><title>Players — Vava Bot4Bots Cup</title></svelte:head>

<div>
  <div class="d-flex justify-content-between align-items-center mb-4">
    <h2 class="text-val-red fw-bold mb-0">Players</h2>
    <div class="card px-4 py-2 d-flex flex-row align-items-center gap-2">
      <span class="fs-4 fw-bold text-white">{players.length}</span>
      <span class="text-secondary small">registered</span>
      {#if players.length >= 20}
        <span class="badge bg-success ms-2">{Math.floor(players.length/5)} teams possible</span>
      {:else}
        <span class="badge bg-secondary ms-2">{Math.floor(players.length/5)} teams</span>
      {/if}
    </div>
  </div>

  {#if loading}
    <p class="text-secondary">Loading...</p>
  {:else if players.length === 0}
    <div class="card p-4 text-center text-secondary">No players registered yet.</div>
  {:else}
    <div class="card overflow-hidden">
      <table class="table table-borderless mb-0 small">
        <thead>
          <tr><th>#</th><th>Player</th><th>Riot ID</th><th>Rank</th><th>Roles</th></tr>
        </thead>
        <tbody>
          {#each sorted as p, i}
            <tr>
              <td class="text-val-red fw-bold">{i+1}</td>
              <td class="fw-semibold">{p.discord_display}</td>
              <td class="text-secondary">{p.riot_id}</td>
              <td class="text-val-gold" style="font-size:0.75rem">{p.rank}</td>
              <td class="text-secondary" style="font-size:0.75rem">{p.roles?.join(', ') || '—'}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</div>
