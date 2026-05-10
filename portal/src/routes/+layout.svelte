<script>
  let { children } = $props();
</script>

<nav class="navbar navbar-expand sticky-top">
  <div class="container-xxl">
    <a href="/" class="navbar-brand d-flex align-items-center gap-2">
      <img src="/logo.png" alt="Vava Bot4Bots Cup" class="logo-img" />
    </a>
    <ul class="navbar-nav gap-1">
      <li class="nav-item"><a href="/" class="nav-link">Bracket</a></li>
      <li class="nav-item"><a href="/teams" class="nav-link">Teams</a></li>
      <li class="nav-item"><a href="/players" class="nav-link">Players</a></li>
    </ul>
  </div>
</nav>

<main class="flex-grow-1">
  <div class="container-xxl py-4">
    {@render children?.()}
  </div>
</main>

<footer class="py-3 text-center">
  <small class="text-secondary">Vava Bot4Bots Cup · Powered by opencode</small>
</footer>
