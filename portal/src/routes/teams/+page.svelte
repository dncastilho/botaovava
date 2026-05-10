<script>
  import { onMount } from 'svelte';
  import { loadTeams } from '$lib/api.js';

  let teams = $state([]);
  let substitutes = $state([]);
  let loading = $state(true);

  onMount(async () => {
    try { const d = await loadTeams(); teams = d.teams || []; substitutes = d.substitutes || []; }
    catch(e) { console.error(e); }
    loading = false;
  });
</script>

<svelte:head><title>Teams — Vava Bot4Bots Cup</title></svelte:head>

<div>
  <h2 class="text-val-red fw-bold mb-4">Teams</h2>

  {#if loading}
    <p class="text-secondary">Loading...</p>
  {:else if teams.length === 0}
    <div class="card p-4 text-center text-secondary">Teams haven't been formed yet.</div>
  {:else}
    <div class="row g-3">
      {#each teams as team}
        <div class="col-md-6 col-lg-4">
          <div class="card h-100">
            <div class="card-body">
              <div class="d-flex align-items-center gap-2 mb-2">
                <span class="text-val-red fw-bold fs-5">#{team.seed}</span>
                <h5 class="card-title mb-0 text-white">{team.name}</h5>
              </div>
              <p class="card-text text-secondary small mb-3">
                Avg Rank: <span class="text-val-gold fw-semibold">{team.average_rank || '?'}</span>
                &middot; Captain: <span class="text-white">{team.players?.[0]?.discord_display || '—'}</span>
              </p>
              <ul class="list-group list-group-flush">
                {#each team.players as p, i}
                  <li class="list-group-item bg-transparent border-val d-flex gap-2 align-items-center text-white small py-2 px-0">
                    <span class="text-val-red fw-bold" style="width:20px">{i+1}</span>
                    <span class="fw-semibold">{p.discord_display}</span>
                    <span class="ms-auto text-val-gold" style="font-size:0.7rem">{p.rank}</span>
                    <span class="text-secondary" style="font-size:0.65rem">{p.roles?.join(', ') || '—'}</span>
                  </li>
                {/each}
              </ul>
            </div>
          </div>
        </div>
      {/each}
    </div>

    {#if substitutes.length > 0}
      <h5 class="text-val-red fw-bold mt-4 mb-2">Substitute Pool</h5>
      <div class="d-flex flex-wrap gap-2">
        {#each substitutes as p}
          <span class="badge bg-val-panel text-white border border-val py-2 px-3">
            {p.discord_display} <span class="text-val-gold">({p.rank})</span>
          </span>
        {/each}
      </div>
    {/if}
  {/if}
</div>
