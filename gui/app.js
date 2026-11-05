// ==========================================
// INSTALLATION PROGRESS STUDIO & DOWNLOAD HUD
// ==========================================
let installPollTimer = null;
let lastInstalledResult = null;

function openInstallProgressModal(title, projectType) {
  const modal = document.getElementById('modal-install-progress');
  if (!modal) return;

  const typeLabel = (projectType || 'package').toUpperCase();
  const typeBadge = document.getElementById('modal-install-type-badge');
  if (typeBadge) typeBadge.textContent = `${typeLabel} INSTALLER`;

  const titleEl = document.getElementById('modal-install-title');
  if (titleEl) titleEl.textContent = `Installing ${title}...`;

  const stepEl = document.getElementById('modal-install-step');
  if (stepEl) stepEl.textContent = 'Connecting to Modrinth API...';

  const percentEl = document.getElementById('modal-install-percent');
  if (percentEl) percentEl.textContent = '0%';

  const barEl = document.getElementById('modal-install-progress-bar');
  if (barEl) {
    barEl.style.width = '0%';
    barEl.style.background = '#10b981';
  }

  const countEl = document.getElementById('modal-install-count-text');
  if (countEl) countEl.textContent = 'Preparing manifest...';

  const spinner = document.getElementById('modal-install-spinner');
  if (spinner) spinner.style.display = 'inline-block';

  const fileEl = document.getElementById('modal-install-current-file');
  if (fileEl) fileEl.textContent = '';

  const logBox = document.getElementById('modal-install-log-box');
  if (logBox) logBox.innerHTML = `<div>[Moon Installer Studio] Preparing ${title}...</div>`;

  const closeBtn = document.getElementById('btn-close-install-modal');
  if (closeBtn) closeBtn.style.display = 'none';

  const minBtn = document.getElementById('btn-minimize-install-modal');
  if (minBtn) {
    minBtn.textContent = 'Hide (Run in Background)';
    minBtn.style.display = 'inline-flex';
  }

  const finishBtn = document.getElementById('btn-finish-install-modal');
  if (finishBtn) finishBtn.style.display = 'none';

  modal.classList.add('active');
}

function closeInstallProgressModal() {
  const modal = document.getElementById('modal-install-progress');
  if (modal) modal.classList.remove('active');
  if (installPollTimer) {
    clearInterval(installPollTimer);
    installPollTimer = null;
  }
  if (lastInstalledResult && typeof reloadLauncherState === 'function') {
    reloadLauncherState();
  }
}

function startPollingInstallProgress() {
  if (installPollTimer) clearInterval(installPollTimer);

  installPollTimer = setInterval(async () => {
    if (!window.pywebview || !window.pywebview.api || !window.pywebview.api.get_install_status) {
      return;
    }
    try {
      const status = await window.pywebview.api.get_install_status();
      if (!status) return;

      const titleEl = document.getElementById('modal-install-title');
      if (titleEl && status.title) {
        titleEl.textContent = status.completed
          ? (status.success ? `✓ ${status.title}` : `✕ ${status.title}`)
          : `Installing ${status.title}...`;
      }

      const stepEl = document.getElementById('modal-install-step');
      if (stepEl && status.step) stepEl.textContent = status.step;

      const percentEl = document.getElementById('modal-install-percent');
      if (percentEl) percentEl.textContent = `${status.percent || 0}%`;

      const barEl = document.getElementById('modal-install-progress-bar');
      if (barEl) {
        barEl.style.width = `${Math.min(100, status.percent || 0)}%`;
        if (status.completed) {
          barEl.style.background = status.success ? '#10b981' : 'var(--pal-coral)';
        } else {
          barEl.style.background = '#10b981';
        }
      }

      const countEl = document.getElementById('modal-install-count-text');
      if (countEl) {
        const speedText = status.speed_str ? ` (${status.speed_str})` : '';
        if (status.total_files > 1) {
          countEl.textContent = `${status.current_index || 0} of ${status.total_files} files${speedText}`;
        } else {
          countEl.textContent = (status.step || 'Processing...') + speedText;
        }
      }

      const fileEl = document.getElementById('modal-install-current-file');
      if (fileEl && status.current_file) {
        fileEl.textContent = status.current_file;
      }

      const logBox = document.getElementById('modal-install-log-box');
      if (logBox && status.logs && status.logs.length > 0) {
        logBox.innerHTML = status.logs.map(l => `<div>${l}</div>`).join('');
        logBox.scrollTop = logBox.scrollHeight;
      }

      if (status.completed) {
        clearInterval(installPollTimer);
        installPollTimer = null;
        lastInstalledResult = status.result;

        const spinner = document.getElementById('modal-install-spinner');
        if (spinner) spinner.style.display = 'none';

        const closeBtn = document.getElementById('btn-close-install-modal');
        if (closeBtn) closeBtn.style.display = 'block';

        const minBtn = document.getElementById('btn-minimize-install-modal');
        if (minBtn) minBtn.textContent = 'Close';

        const finishBtn = document.getElementById('btn-finish-install-modal');
        if (finishBtn) {
          if (status.success) {
            finishBtn.style.display = 'inline-flex';
            finishBtn.textContent = (status.type === 'modpack') ? 'Switch & Play' : 'Done';
          } else {
            finishBtn.style.display = 'none';
          }
        }

        if (status.success) {
          showToast(`✓ ${status.title || 'Package'} installed successfully!`);
          if (typeof reloadLauncherState === 'function') {
            await reloadLauncherState();
          }
          const pType = status.type || (status.result && status.result.type);
          if (pType === 'mod' && typeof loadMods === 'function') {
            await loadMods();
          }
        } else {
          showToast(`Install failed: ${status.error || 'Error'}`, true);
        }
      }
    } catch (e) {
      console.error("Error polling install progress:", e);
    }
  }, 250);
}

// Moon Launcher Studio Desktop GUI - Full Feature Client Logic

let appState = {
  config: {},
  versions: [],
  active_version: '',
  specs: {},
  servers: [],
  friends: [],
  mods: []
};

// ==========================================
// TOAST NOTIFICATION
// ==========================================
function showToast(message, isError = false) {
  const toast = document.getElementById('app-toast');
  if (!toast) return;
  toast.innerText = message;
  toast.style.display = 'block';
  toast.style.background = isError ? 'var(--pal-coral)' : 'var(--pal-mint)';
  toast.style.color = 'var(--ink-primary)';
  setTimeout(() => {
    toast.style.display = 'none';
  }, 3500);
}

// ==========================================
// NAVIGATION TABS
// ==========================================
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const target = btn.dataset.tab;
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.view-panel').forEach(p => p.classList.remove('active'));
    
    btn.classList.add('active');
    const panel = document.getElementById(target);
    if (panel) panel.classList.add('active');

    // Trigger lazy-loading for active tabs
    if (target === 'view-play') {
      if (typeof reloadLauncherState === 'function') reloadLauncherState();
    } else if (target === 'view-mods') {
      loadMods();
    } else if (target === 'view-catalog' && !window.catalogLoaded) {
      loadCatalog();
    } else if (target === 'view-multiplayer') {
      loadServers();
    } else if (target === 'view-crash') {
      loadCrashDiagnostics();
      loadLatestLog();
    }
  });
});

// ==========================================
// INITIALIZATION & PYWEBVIEW BRIDGE
// ==========================================
window.addEventListener('pywebviewready', () => {
  initApp();
});

setTimeout(() => {
  if (!window.appInitialized) {
    initApp();
  }
}, 600);

async function reloadLauncherState() {
  if (window.pywebview && window.pywebview.api && window.pywebview.api.get_launcher_state) {
    try {
      const state = await window.pywebview.api.get_launcher_state();
      if (state) {
        applyLauncherState(state);
      }
      return state;
    } catch (err) {
      console.error('Failed to reload launcher state:', err);
    }
  }
  return null;
}
window.loadLauncherState = reloadLauncherState;
window.reloadLauncherState = reloadLauncherState;

async function initApp() {
  window.appInitialized = true;
  if (window.pywebview && window.pywebview.api) {
    const state = await reloadLauncherState();
    if (!state) {
      showToast('Could not reach launcher engine', true);
    }
  } else {
    // Browser mock state preview
    applyLauncherState({
      config: {
        username: 'JustMichellee',
        version_name: 'CursedWalkingZS',
        ram_max_gb: 8,
        java_path: 'C:\\Program Files\\Java\\jdk-21\\bin\\javaw.exe',
        width: 1280,
        height: 720,
        fullscreen: false,
        discord_rpc: true,
        jvm_g1gc_preset: true
      },
      active_version: 'CursedWalkingZS',
      versions: [
        { name: 'CursedWalkingZS', loader: 'Forge', mc_version: '1.20.1', mod_count: 85, size_mb: 240.5 },
        { name: 'NightfallCraft 2.2.9.7', loader: 'Forge', mc_version: '1.20.1', mod_count: 92, size_mb: 310.2 },
        { name: 'Fabric 1.20.1', loader: 'Fabric', mc_version: '1.20.1', mod_count: 14, size_mb: 45.0 },
        { name: '1.20.1 Vanilla', loader: 'Vanilla', mc_version: '1.20.1', mod_count: 0, size_mb: 0.0 }
      ],
      specs: {
        cpu: 'AMD Ryzen 7 5800X 8-Core Processor',
        ram_total_gb: 32.0,
        ram_avail_gb: 18.5,
        os: 'Windows 11',
        detected_javas: [
          { path: 'C:\\Java\\jdk-21\\bin\\javaw.exe', major: 21, vendor: 'Java 21 (Eclipse Temurin)' },
          { path: 'C:\\Java\\jdk-17\\bin\\javaw.exe', major: 17, vendor: 'Java 17 (Microsoft Gamma)' },
          { path: 'C:\\Java\\jre1.8.0_281\\bin\\javaw.exe', major: 8, vendor: 'Java 8 (Oracle Legacy)' }
        ]
      },
      servers: [
        { name: 'CubeCraft Games', address: 'play.cubecraft.net:25565', category: 'Survival & Bedwars', ping: { online: true, latency: 162, motd: 'CubeCraft Network', players_online: 495, players_max: 5000 } }
      ],
      launcher_version: 'v2.4.5'
    });
  }
}

// Apply State to DOM
function applyLauncherState(state) {
  appState = state;
  const cfg = state.config || {};
  const username = cfg.username || 'Player';
  const savedLocalVer = localStorage.getItem('moon_active_version');
  const activeVer = state.active_version || cfg.version_name || savedLocalVer || '1.20.1';
  if (activeVer) {
    try { localStorage.setItem('moon_active_version', activeVer); } catch (e) {}
  }

  // Sync running status on state load
  if (state.is_game_running) {
    isGameRunning = true;
    updateLaunchButtonState('running', state.game_pid);
    startGameStatusWatcher();
  } else if (!isGameLaunching) {
    isGameRunning = false;
    updateLaunchButtonState('idle');
  }

  // 1. Header Player Chip
  const headName = document.getElementById('header-player-name');
  if (headName) headName.innerText = username;
  const dashName = document.getElementById('dash-username-display');
  if (dashName) dashName.innerText = username;
  const quickUser = document.getElementById('input-quick-username');
  if (quickUser) quickUser.value = username;

  // Prioritize custom skin avatar from backend or fallback to Minotar
  const avatarUrl = state.avatar_url || cfg.custom_skin_url || 'https://minotar.net/bust/Steve/128.png';
  const headAvatar = document.getElementById('header-avatar-img');
  if (headAvatar) headAvatar.src = avatarUrl;
  const dashAvatar = document.getElementById('dash-avatar-bust');
  if (dashAvatar) dashAvatar.src = avatarUrl;

  // 2. Active Version Title & Badges
  const titleEl = document.getElementById('display-version-title');
  if (titleEl) titleEl.innerText = activeVer;
  const modsTitle = document.getElementById('mods-studio-title');
  if (modsTitle) modsTitle.innerText = activeVer + ' Mods';

  // Find active version info in versions array
  const activeMeta = (state.versions || []).find(v => v.name === activeVer) || {
    name: activeVer,
    loader: 'Forge',
    mc_version: '1.20.1',
    mod_count: 0,
    size_mb: 0
  };

  const badgeLoader = document.getElementById('badge-loader');
  if (badgeLoader) badgeLoader.innerText = 'Loader: ' + (activeMeta.loader || 'Vanilla');
  const badgeMc = document.getElementById('badge-mc-ver');
  if (badgeMc) badgeMc.innerText = 'MC: ' + (activeMeta.mc_version || '1.20.1');
  const badgeMods = document.getElementById('badge-mod-count');
  if (badgeMods) badgeMods.innerText = 'Mods: ' + (activeMeta.mod_count || 0);
  const badgeSize = document.getElementById('badge-disk-size');
  if (badgeSize) badgeSize.innerText = 'Size: ' + (activeMeta.size_mb || 0) + ' MB';

  // 3. Version Select Dropdown
  const selectVer = document.getElementById('select-active-version');
  if (selectVer) {
    selectVer.innerHTML = '';
    (state.versions || []).forEach(v => {
      const opt = document.createElement('option');
      opt.value = v.name;
      opt.innerText = `${v.name} (${v.loader || 'Vanilla'} ${v.mc_version || ''})`;
      if (v.name === activeVer) opt.selected = true;
      selectVer.appendChild(opt);
    });
    if (activeVer) {
      selectVer.value = activeVer;
    }
  }

  // 4. RAM Sliders & Values
  const ramVal = cfg.ram_max_gb || 8;
  const ramDisp = document.getElementById('display-ram-val');
  if (ramDisp) ramDisp.innerText = ramVal + ' GB';
  const ramSlider = document.getElementById('slider-quick-ram');
  if (ramSlider) ramSlider.value = ramVal;
  const setRamSlider = document.getElementById('setting-ram-slider');
  if (setRamSlider) setRamSlider.value = ramVal;
  const setRamLabel = document.getElementById('setting-ram-label');
  if (setRamLabel) setRamLabel.innerText = ramVal + ' GB';

  // 5. Settings Inputs
  const javaIn = document.getElementById('setting-java-path');
  if (javaIn) javaIn.value = cfg.java_path || '';
  const wIn = document.getElementById('setting-width');
  if (wIn) wIn.value = cfg.width || 1280;
  const hIn = document.getElementById('setting-height');
  if (hIn) hIn.value = cfg.height || 720;
  const fsIn = document.getElementById('setting-fullscreen');
  if (fsIn) fsIn.checked = !!cfg.fullscreen;
  const rpcIn = document.getElementById('setting-discord-rpc');
  if (rpcIn) rpcIn.checked = cfg.discord_rpc !== false;
  const g1gcIn = document.getElementById('setting-jvm-g1gc');
  if (g1gcIn) g1gcIn.checked = cfg.jvm_g1gc_preset !== false;

  // 1b. Moon ID Badge & Banner
  const moonId = state.moon_id || (cfg.moon_id) || 'MOON-4821';
  const badgeId = document.getElementById('dash-moon-id-badge');
  if (badgeId) {
    badgeId.innerText = moonId;
    badgeId.onclick = () => {
      navigator.clipboard.writeText(moonId);
      showToast('Copied Moon ID: ' + moonId);
    };
  }
  const myMoonIdDisp = document.getElementById('my-moon-id-display');
  if (myMoonIdDisp) myMoonIdDisp.innerText = moonId;

  // 6. Specs & Hardware
  const specs = state.specs || {};
  const cpuEl = document.getElementById('spec-cpu-name');
  if (cpuEl) cpuEl.innerText = specs.cpu || 'x86_64 Processor';
  const gpuEl = document.getElementById('spec-gpu-name');
  if (gpuEl) gpuEl.innerText = specs.gpu || 'Standard Graphics Adapter';
  const ramSpec = document.getElementById('spec-ram-summary');
  if (ramSpec) ramSpec.innerText = `${specs.ram_avail_gb || 8} GB Available / ${specs.ram_total_gb || 16} GB Total`;
  const osEl = document.getElementById('spec-os-name');
  if (osEl) osEl.innerText = specs.os || 'Windows';

  // Render Friends List
  renderFriendsList(state.friends || []);

  // Render Java Runtimes list
  const jList = document.getElementById('spec-javas-list');
  if (jList && specs.detected_javas) {
    jList.innerHTML = '';
    specs.detected_javas.forEach(j => {
      const row = document.createElement('div');
      row.style.background = '#ffffff';
      row.style.border = '2px solid var(--ink-primary)';
      row.style.borderRadius = '6px';
      row.style.padding = '8px 10px';
      row.style.fontSize = '0.80rem';
      row.style.display = 'flex';
      row.style.justifyContent = 'space-between';
      row.style.alignItems = 'center';
      row.innerHTML = `
        <div>
          <span class="badge-tag" style="background: var(--pal-mint); font-size: 0.70rem; padding: 2px 6px;">Java ${j.major}</span>
          <span style="font-weight: 700; margin-left: 6px;">${j.vendor || 'Runtime'}</span>
        </div>
        <button class="btn btn-secondary btn-use-java" data-path="${j.path}" style="padding: 2px 8px; font-size: 0.72rem;">Use</button>
      `;
      jList.appendChild(row);
    });

    jList.querySelectorAll('.btn-use-java').forEach(btn => {
      btn.addEventListener('click', () => {
        const p = btn.dataset.path;
        if (javaIn) javaIn.value = p;
        showToast('Selected: Java ' + p.split('\\').pop());
      });
    });
  }

  // 7. Render Installed Instances Grid
  renderInstancesGrid(state.versions || [], activeVer);
}


// ==========================================
// FRIENDS LIST RENDERER
// ==========================================
function renderFriendsList(friends) {
  const container = document.getElementById('friends-presence-list');
  if (!container) return;
  container.innerHTML = '';

  if (!friends || !friends.length) {
    container.innerHTML = '<div style="font-size: 0.82rem; color: var(--ink-muted); text-align: center; padding: 14px; font-weight: 600;">No friends added yet. Add a friend by username or Moon ID!</div>';
    return;
  }

  friends.forEach(f => {
    const isOnline = f.status === 'online' || f.status === 'in-game';
    const row = document.createElement('div');
    row.style.cssText = 'background: #ffffff; border: 2px solid var(--ink-primary); border-radius: 8px; padding: 8px 12px; display: flex; justify-content: space-between; align-items: center; box-shadow: 2px 2px 0px var(--ink-primary);';

    row.innerHTML = `
      <div style="display: flex; align-items: center; gap: 8px;">
        <span class="ping-dot ${isOnline ? 'online' : 'offline'}"></span>
        <div>
          <div style="font-weight: 800; font-size: 0.88rem; color: var(--ink-primary);">${f.username || 'Friend'}</div>
          ${f.player_id ? `<div style="font-family: var(--font-mono); font-size: 0.70rem; color: var(--ink-muted);">${f.player_id}</div>` : ''}
        </div>
      </div>
      <div style="display: flex; align-items: center; gap: 6px;">
        <span class="badge-tag" style="background: ${isOnline ? 'var(--pal-mint)' : 'var(--pal-cream)'}; font-size: 0.70rem; padding: 2px 7px;">
          ${(f.status || 'offline').toUpperCase()}
        </span>
      </div>
    `;
    container.appendChild(row);
  });
}

// ==========================================
// RENDER INSTANCES GRID
// ==========================================
function renderInstancesGrid(versions, activeVer) {
  const container = document.getElementById('instances-card-grid');
  const countBadge = document.getElementById('total-instances-badge');
  if (countBadge) countBadge.innerText = `${versions.length} Instances`;
  if (!container) return;

  container.innerHTML = '';
  if (!versions.length) {
    container.innerHTML = '<div style="padding: 20px; color: var(--ink-muted);">No installed instances found.</div>';
    return;
  }

  versions.forEach(v => {
    const isActive = v.name === activeVer;
    const card = document.createElement('div');
    card.className = `instance-card-box ${isActive ? 'active-card' : ''}`;
    
    card.innerHTML = `
      <div>
        <div style="display: flex; justify-content: space-between; align-items: flex-start; min-height: 28px; margin-bottom: 8px; gap: 8px;">
          <h4 style="font-size: 1.05rem; font-weight: 900; line-height: 1.3; flex: 1; word-break: break-word; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;" title="${v.name}">${v.name}</h4>
          ${isActive ? '<span class="badge-tag" style="background: var(--pal-coral); flex-shrink: 0;">ACTIVE</span>' : ''}
        </div>
        <div style="display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 12px; min-height: 28px;">
          <span class="badge-tag" style="background: #ffffff;">${v.loader || 'Vanilla'}</span>
          <span class="badge-tag" style="background: #ffffff;">${v.mc_version || '1.20.1'}</span>
          <span class="badge-tag" style="background: #ffffff;">${v.mod_count || 0} Mods</span>
          <span class="badge-tag" style="background: #ffffff;">${v.size_mb || 0} MB</span>
        </div>
      </div>
      <div style="display: flex; gap: 6px;">
        <button class="btn ${isActive ? 'btn-primary' : 'btn-mint'} btn-switch-inst" data-name="${v.name}" style="flex: 1; padding: 7px 10px; font-size: 0.82rem;">
          ${isActive ? 'Play Active' : 'Switch'}
        </button>
        <button class="btn btn-white btn-share-inst" data-name="${v.name}" title="Bagi Modpack ini ke teman" style="padding: 7px 10px;">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"><path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"/><polyline points="16 6 12 2 8 6"/><line x1="12" x2="12" y1="2" y2="15"/></svg>
        </button>
        <button class="btn btn-secondary btn-open-inst" data-name="${v.name}" title="Open Folder" style="padding: 7px 10px;">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"><path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/></svg>
        </button>
        <button class="btn btn-danger btn-delete-inst" data-name="${v.name}" title="Uninstall Instance" style="padding: 7px 10px;">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
        </button>
      </div>
    `;

    // Switch
    card.querySelector('.btn-switch-inst').addEventListener('click', async () => {
      if (isActive) {
        launchGame();
      } else {
        await switchVersion(v.name);
      }
    });

    // Share Modpack
    const btnShareInst = card.querySelector('.btn-share-inst');
    if (btnShareInst) {
      btnShareInst.addEventListener('click', () => {
        openShareModal(v.name);
      });
    }

    // Open Folder
    card.querySelector('.btn-open-inst').addEventListener('click', () => {
      openFolder('version', v.name);
    });

    // Delete Instance
    card.querySelector('.btn-delete-inst').addEventListener('click', async () => {
      if (confirm(`Are you sure you want to completely delete instance '${v.name}'? All mods, saves, and configs for this version will be uninstalled.`)) {
        await deleteVersion(v.name);
      }
    });

    container.appendChild(card);
  });
}

async function switchVersion(verName) {
  if (window.pywebview && window.pywebview.api) {
    try {
      try { localStorage.setItem('moon_active_version', verName); } catch (e) {}
      showToast('Switching instance to ' + verName + '...');
      await window.pywebview.api.set_active_version(verName);
      const state = await window.pywebview.api.get_launcher_state();
      applyLauncherState(state);
      showToast('Active instance: ' + verName);
    } catch (e) {
      showToast('Error switching version: ' + e, true);
    }
  }
}

async function deleteVersion(verName) {
  if (window.pywebview && window.pywebview.api) {
    try {
      showToast('Uninstalling ' + verName + '...');
      const res = await window.pywebview.api.delete_version(verName);
      if (res && res.success) {
        showToast('Successfully uninstalled ' + verName);
        const state = await window.pywebview.api.get_launcher_state();
        applyLauncherState(state);
      } else {
        showToast('Failed to delete: ' + (res.error || 'Unknown error'), true);
      }
    } catch (e) {
      showToast('Delete error: ' + e, true);
    }
  }
}

let isGameLaunching = false;
let isGameRunning = false;
let gameStatusPollInterval = null;

function updateLaunchButtonState(state, pid = null) {
  const btn = document.getElementById('btn-launch-game');
  if (!btn) return;

  if (state === 'launching') {
    btn.disabled = true;
    btn.classList.add('loading');
    btn.classList.remove('running');
    btn.innerHTML = `
      <div class="btn-spinner"></div>
      <span id="launch-btn-label">LAUNCHING MINECRAFT...</span>
    `;
  } else if (state === 'running') {
    btn.disabled = false;
    btn.classList.remove('loading');
    btn.classList.add('running');
    const pidText = pid ? ` (PID: ${pid})` : '';
    btn.innerHTML = `
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
        <circle cx="12" cy="12" r="10"/>
        <polygon points="10 8 16 12 10 16 10 8" fill="currentColor"/>
      </svg>
      <span id="launch-btn-label">PLAYING MINECRAFT${pidText}</span>
    `;
  } else {
    btn.disabled = false;
    btn.classList.remove('loading', 'running');
    btn.innerHTML = `
      <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" stroke="none">
        <polygon points="5 3 19 12 5 21 5 3"/>
      </svg>
      <span id="launch-btn-label">PLAY MINECRAFT</span>
    `;
  }
}

function startGameStatusWatcher() {
  if (gameStatusPollInterval) clearInterval(gameStatusPollInterval);
  gameStatusPollInterval = setInterval(async () => {
    if (!window.pywebview || !window.pywebview.api || !window.pywebview.api.get_game_status) return;
    try {
      const status = await window.pywebview.api.get_game_status();
      if (!status.is_running && isGameRunning) {
        isGameRunning = false;
        clearInterval(gameStatusPollInterval);
        gameStatusPollInterval = null;
        updateLaunchButtonState('idle');
        showToast('Minecraft session ended.');

        if (window.pywebview.api.get_crash_diagnostics) {
          try {
            const diag = await window.pywebview.api.get_crash_diagnostics(appState.active_version);
            if (diag && diag.crashes && diag.crashes.length > 0) {
              const latest = diag.crashes[0];
              const crashAge = (Date.now() - new Date(latest.timestamp).getTime()) / 1000;
              if (crashAge < 60) {
                showToast(`Game closed with issue: ${latest.error_type || 'Premature exit'}. Check Crash Diagnostics tab.`, true);
              }
            }
          } catch (_) {}
        }
      }
    } catch (_) {}
  }, 2500);
}

async function launchGame(directServer = null) {
  if (isGameLaunching) {
    showToast('Minecraft is currently starting, please wait...');
    return;
  }
  if (isGameRunning) {
    showToast('Minecraft is already running!', false);
    return;
  }

  const verName = appState.active_version || '1.20.1';
  isGameLaunching = true;
  updateLaunchButtonState('launching');
  showToast(`Starting Minecraft (${verName})...`);

  if (window.pywebview && window.pywebview.api) {
    try {
      const res = await window.pywebview.api.launch_game(directServer);
      if (res && res.success) {
        isGameLaunching = false;
        isGameRunning = true;
        updateLaunchButtonState('running', res.pid);
        showToast(`Minecraft (${res.version_name || verName}) launched successfully!`);
        startGameStatusWatcher();
      } else {
        isGameLaunching = false;
        isGameRunning = false;
        updateLaunchButtonState('idle');
        const errMsg = res && res.error ? res.error : 'Failed to launch Minecraft';
        showToast(errMsg, true);
      }
    } catch (err) {
      isGameLaunching = false;
      isGameRunning = false;
      updateLaunchButtonState('idle');
      showToast('Launch error: ' + err, true);
    }
  } else {
    setTimeout(() => {
      isGameLaunching = false;
      isGameRunning = true;
      updateLaunchButtonState('running');
      showToast(`Minecraft (${verName}) launched (Browser Preview Mode)`);
      setTimeout(() => {
        isGameRunning = false;
        updateLaunchButtonState('idle');
      }, 5000);
    }, 1200);
  }
}

function openFolder(folderType, verName = null) {
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.open_folder(folderType, verName);
  } else {
    showToast('Opened folder: ' + folderType);
  }
}

// Hero Play Launch Button
const btnLaunch = document.getElementById('btn-launch-game');
if (btnLaunch) {
  btnLaunch.addEventListener('click', () => launchGame());
}

// Preflight Check Button
const btnPreflight = document.getElementById('btn-quick-test');
if (btnPreflight) {
  btnPreflight.addEventListener('click', () => {
    if (window.pywebview && window.pywebview.api) {
      window.pywebview.api.run_preflight_test(appState.active_version);
      showToast('Opened Preflight diagnostic tester');
    }
  });
}

// Quick Refresh
const btnRefresh = document.getElementById('btn-quick-refresh');
if (btnRefresh) {
  btnRefresh.addEventListener('click', () => initApp());
}

// Version Selector Dropdown change
const selectVer = document.getElementById('select-active-version');
if (selectVer) {
  selectVer.addEventListener('change', (e) => {
    if (e.target.value) switchVersion(e.target.value);
  });
}

// Quick Folder Buttons
document.querySelectorAll('.folder-pill-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    openFolder(btn.dataset.folder);
  });
});

// Quick RAM Slider
const ramSlider = document.getElementById('slider-quick-ram');
const ramDisplay = document.getElementById('display-ram-val');
if (ramSlider && ramDisplay) {
  ramSlider.addEventListener('input', (e) => {
    ramDisplay.innerText = e.target.value + ' GB';
  });
  ramSlider.addEventListener('change', async (e) => {
    const gb = parseInt(e.target.value);
    if (window.pywebview && window.pywebview.api) {
      await window.pywebview.api.set_ram(gb);
      showToast('RAM updated to ' + gb + ' GB');
    }
  });
}

// Username Save
const btnSaveUser = document.getElementById('btn-save-username');
const inUser = document.getElementById('input-quick-username');
if (btnSaveUser && inUser) {
  btnSaveUser.addEventListener('click', async () => {
    const val = inUser.value.trim();
    if (!val) return;
    if (window.pywebview && window.pywebview.api) {
      const res = await window.pywebview.api.set_player_name(val);
      showToast('Saved player: ' + val);
      if (res && res.avatar_url) {
        const headAvatar = document.getElementById('header-avatar-img');
        if (headAvatar) headAvatar.src = res.avatar_url;
        const dashAvatar = document.getElementById('dash-avatar-bust');
        if (dashAvatar) dashAvatar.src = res.avatar_url;
        appState.avatar_url = res.avatar_url;
      }
      const state = await window.pywebview.api.get_launcher_state();
      applyLauncherState(state);
    }
  });
}

// ==========================================
// VIEW 2: MOD MANAGER
// ==========================================
async function loadMods() {
  const container = document.getElementById('mods-list-container');
  const countPill = document.getElementById('mods-count-pill');
  if (!container) return;
  container.innerHTML = '<div style="text-align: center; padding: 30px; font-weight: 700; color: var(--ink-muted);">Scanning mods for active version...</div>';

  if (window.pywebview && window.pywebview.api) {
    try {
      const res = await window.pywebview.api.get_mods_list(appState.active_version);
      appState.mods = res.mods || [];
      renderModsList(appState.mods);
    } catch (e) {
      container.innerHTML = `<div style="text-align: center; padding: 20px; color: var(--pal-coral); font-weight: 800;">Error reading mods: ${e}</div>`;
    }
  } else {
    // Mock mods
    appState.mods = [
      { name: 'create-1.20.1-0.5.1.f', filename: 'create-1.20.1-0.5.1.f.jar', enabled: true, size_kb: 14200 },
      { name: 'rubidium-mc1.20.1-0.7.1', filename: 'rubidium-mc1.20.1-0.7.1.jar', enabled: true, size_kb: 2100 },
      { name: 'oculus-mc1.20.1-1.6.15', filename: 'oculus-mc1.20.1-1.6.15.jar', enabled: true, size_kb: 3400 },
      { name: 'jei-1.20.1-forge-15.3.0.4', filename: 'jei-1.20.1-forge-15.3.0.4.jar', enabled: true, size_kb: 1850 },
      { name: 'ferritecore-6.0.1-forge', filename: 'ferritecore-6.0.1-forge.jar.disabled', enabled: false, size_kb: 340 }
    ];
    renderModsList(appState.mods);
  }
}

function renderModsList(mods) {
  const container = document.getElementById('mods-list-container');
  const countPill = document.getElementById('mods-count-pill');
  if (!container) return;

  const enabledCount = mods.filter(m => m.enabled).length;
  if (countPill) countPill.innerText = `${enabledCount} / ${mods.length} Enabled`;

  container.innerHTML = '';
  if (!mods.length) {
    container.innerHTML = '<div style="text-align: center; padding: 40px; font-weight: 700; color: var(--ink-muted);">No mods found in this instance. Use the Catalog to install mods!</div>';
    return;
  }

  mods.forEach(m => {
    const row = document.createElement('div');
    row.className = `mod-item-row ${m.enabled ? '' : 'disabled'}`;
    row.dataset.name = m.name.toLowerCase();

    row.innerHTML = `
      <div style="flex: 1; overflow: hidden;">
        <div style="font-weight: 800; font-size: 0.95rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
          ${m.name}
        </div>
        <div style="display: flex; gap: 8px; align-items: center; margin-top: 2px;">
          <span style="font-family: var(--font-mono); font-size: 0.76rem; color: var(--ink-muted);">${m.filename}</span>
          <span class="badge-tag" style="background: #ffffff; font-size: 0.70rem; padding: 1px 6px;">${m.size_kb} KB</span>
        </div>
      </div>

      <div style="display: flex; align-items: center; gap: 12px; flex-shrink: 0;">
        <label class="tactile-switch" title="Toggle Mod Enabled/Disabled">
          <input type="checkbox" class="mod-toggle-cb" data-filename="${m.filename}" ${m.enabled ? 'checked' : ''}>
          <span class="tactile-slider"></span>
        </label>
        <button class="btn btn-secondary btn-del-mod" data-filename="${m.filename}" title="Move to backup (_backup_unused_mods)" style="padding: 6px 10px;">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
        </button>
      </div>
    `;

    // Toggle switch
    row.querySelector('.mod-toggle-cb').addEventListener('change', async (e) => {
      const fn = e.target.dataset.filename;
      if (window.pywebview && window.pywebview.api) {
        const res = await window.pywebview.api.toggle_mod(fn, appState.active_version);
        if (res && res.success) {
          showToast(`Mod toggled: ${res.new_name}`);
          loadMods();
        } else {
          showToast(`Error toggling mod: ${res.error || 'Failed'}`, true);
          e.target.checked = !e.target.checked;
        }
      } else {
        m.enabled = !m.enabled;
        renderModsList(mods);
      }
    });

    // Delete / Backup mod
    row.querySelector('.btn-del-mod').addEventListener('click', async () => {
      if (confirm(`Move mod '${m.filename}' to safe backup directory?`)) {
        if (window.pywebview && window.pywebview.api) {
          await window.pywebview.api.delete_mod(m.filename, appState.active_version);
          showToast('Moved to backup: ' + m.filename);
          loadMods();
        } else {
          appState.mods = appState.mods.filter(x => x.filename !== m.filename);
          renderModsList(appState.mods);
        }
      }
    });

    container.appendChild(row);
  });
}

// Live Mod Search
const inModSearch = document.getElementById('input-mod-search');
if (inModSearch) {
  inModSearch.addEventListener('input', (e) => {
    const q = e.target.value.toLowerCase().trim();
    document.querySelectorAll('.mod-item-row').forEach(row => {
      row.style.display = row.dataset.name.includes(q) ? 'flex' : 'none';
    });
  });
}

// Open Mods Folder
const btnModsFolder = document.getElementById('btn-mods-open-folder');
if (btnModsFolder) {
  btnModsFolder.addEventListener('click', () => openFolder('mods'));
}

// Refresh Mods
const btnModsRefresh = document.getElementById('btn-mods-refresh');
if (btnModsRefresh) {
  btnModsRefresh.addEventListener('click', () => loadMods());
}

// ==========================================
// ==========================================
// VIEW 3: MOD BROWSER
// Matches Moon Web explore/page.tsx & ModCard.tsx exactly
// ==========================================
let catalogQuery = '';
let catalogType = 'all';
let catalogSort = 'relevance';
let catalogPage = 1;
const catalogPageSize = 24;
let catalogTotalHits = 0;
let catalogSearchTimer = null;

const sortLabels = {
  relevance: 'Most Relevant',
  downloads: 'Most Downloads',
  follows: 'Most Followed',
  newest: 'Recently Added',
  updated: 'Recently Updated'
};

function formatDownloadsCount(num) {
  if (!num) return '0';
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
  return num.toLocaleString();
}

function getPaginationItems(currentPage, totalPages) {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, i) => i + 1);
  }
  let left, right;
  if (currentPage <= 3) {
    left = 1; right = 5;
  } else if (currentPage >= totalPages - 2) {
    left = totalPages - 4; right = totalPages;
  } else {
    left = currentPage - 2; right = currentPage + 2;
  }
  const items = [];
  if (left > 1) {
    items.push(1);
    if (left > 2) items.push('...');
  }
  for (let i = left; i <= right; i++) items.push(i);
  if (right < totalPages) {
    if (right < totalPages - 1) items.push('...');
    items.push(totalPages);
  }
  return items;
}

async function loadCatalog() {
  window.catalogLoaded = true;
  const grid = document.getElementById('catalog-results-grid');
  if (!grid) return;
  grid.innerHTML = '<div style="text-align: center; padding: 48px; grid-column: 1 / -1; font-weight: 700; color: var(--ink-muted);">Loading packages from Modrinth...</div>';

  const offset = (catalogPage - 1) * catalogPageSize;
  let results = null;

  if (window.pywebview && window.pywebview.api && window.pywebview.api.search_modrinth) {
    try {
      results = await window.pywebview.api.search_modrinth(catalogQuery, catalogType, catalogSort, offset, catalogPageSize);
    } catch (e) {
      console.error(e);
    }
  }

  // Fallback direct Modrinth API if pywebview offline
  if (!results || !results.hits) {
    try {
      let url = `https://api.modrinth.com/v2/search?limit=${catalogPageSize}&offset=${offset}&index=${catalogSort}`;
      if (catalogQuery) url += `&query=${encodeURIComponent(catalogQuery)}`;
      if (catalogType && catalogType !== 'all') {
        url += `&facets=[["project_type:${catalogType}"]]`;
      }
      const resp = await fetch(url);
      results = await resp.json();
    } catch (err) {
      grid.innerHTML = '<div style="text-align: center; padding: 48px; grid-column: 1 / -1; color: var(--pal-coral); font-weight: 800;">Failed to load catalog packages. Check internet connection.</div>';
      return;
    }
  }

  catalogTotalHits = results.total_hits || (results.hits ? results.hits.length : 0);
  renderCatalog(results.hits || []);
  renderCatalogPagination();
}

function renderCatalog(hits) {
  const grid = document.getElementById('catalog-results-grid');
  if (!grid) return;
  grid.innerHTML = '';

  // Update results header subtext matching website
  const subCount = document.getElementById('catalog-sub-count');
  if (subCount) subCount.innerText = hits.length;
  const subTotal = document.getElementById('catalog-sub-total');
  if (subTotal) subTotal.innerText = catalogTotalHits.toLocaleString();
  const subPage = document.getElementById('catalog-sub-page');
  if (subPage) subPage.innerText = catalogPage;
  const maxPage = Math.min(Math.max(1, Math.ceil(catalogTotalHits / catalogPageSize)), 500);
  const subMaxPage = document.getElementById('catalog-sub-maxpage');
  if (subMaxPage) subMaxPage.innerText = maxPage;

  if (!hits.length) {
    grid.innerHTML = '<div style="text-align: center; padding: 48px; grid-column: 1 / -1; font-weight: 700; color: var(--ink-muted);">No community packages matched your search.</div>';
    return;
  }

  hits.forEach(item => {
    const card = document.createElement('article');
    card.style.cssText = 'display: flex; flex-direction: column; padding: 20px; background: #ffffff; border: 2px solid var(--ink-primary); border-radius: 12px; box-shadow: 4px 4px 0px var(--ink-primary); min-height: 250px;';

    const iconUrl = item.icon_url || 'https://minotar.net/bust/Steve/64.png';
    const downloadsFormatted = formatDownloadsCount(item.downloads || 0);
    const authorName = item.author || 'Creator';
    const projType = (item.project_type || 'mod').toUpperCase();
    const cats = (item.categories || []).slice(0, 2).join(', ');

    card.innerHTML = `
      <div style="display: flex; gap: 14px; margin-bottom: 14px;">
        <!-- Project Icon with Mint Box & Offset Shadow matching ModCard -->
        <div style="width: 56px; height: 56px; border-radius: 10px; overflow: hidden; flex-shrink: 0; background: var(--pal-mint); border: 2px solid var(--ink-primary); box-shadow: 2px 2px 0px var(--ink-primary); display: flex; align-items: center; justify-content: center;">
          <img src="${iconUrl}" alt="${item.title}" style="width: 100%; height: 100%; object-fit: cover;" onerror="this.src='https://minotar.net/bust/Steve/64.png'">
        </div>

        <!-- Header Details -->
        <div style="flex: 1; min-width: 0;">
          <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px; flex-wrap: wrap;">
            <span class="badge-tag" style="background: var(--pal-periwinkle); text-transform: uppercase; font-size: 0.70rem; padding: 2px 7px;">${projType}</span>
            <span style="font-size: 0.82rem; color: var(--ink-secondary); font-weight: 600;">
              by <strong style="color: var(--ink-primary); font-weight: 800;">${authorName}</strong>
            </span>
          </div>

          <h3 style="font-size: 1.1rem; font-weight: 900; line-height: 1.3; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: var(--ink-primary);" title="${item.title}">
            ${item.title}
          </h3>

          <div style="display: flex; align-items: center; gap: 10px; margin-top: 6px; font-size: 0.82rem;">
            <span style="display: flex; align-items: center; gap: 4px; color: var(--ink-primary); font-weight: 800;">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/></svg>
              ${downloadsFormatted}
            </span>
            ${cats ? `<span style="background: var(--pal-cream); border: 1.5px solid var(--ink-primary); border-radius: 4px; padding: 1px 6px; font-size: 0.72rem; font-weight: 700; color: var(--ink-primary); max-width: 130px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${cats}</span>` : ''}
          </div>
        </div>
      </div>

      <!-- Description matching ModCard 2-line clamp -->
      <p style="font-size: 0.86rem; color: var(--ink-secondary); line-height: 1.5; font-weight: 600; flex: 1; margin-bottom: 16px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">
        ${item.description || 'No description provided for this package.'}
      </p>

      <!-- Actions Row: 1-Click Install Button + External Link -->
      <div style="display: flex; gap: 8px; margin-top: auto;">
        <button class="btn btn-primary btn-install-pkg" data-slug="${item.slug || item.project_id}" style="flex: 1; padding: 9px 12px; font-size: 0.88rem; gap: 6px;" title="Install into Moon Launcher">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/><path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"/></svg>
          <span>Install</span>
        </button>
        <button class="btn btn-white btn-external-link" data-url="https://modrinth.com/${item.project_type || 'mod'}/${item.slug || item.project_id}" style="padding: 9px 12px;" title="View on Modrinth">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" x2="21" y1="14" y2="3"/></svg>
        </button>
      </div>
    `;

    // Install handler (supports modpack, mod, resourcepack, shader with Real-Time HUD)
    card.querySelector('.btn-install-pkg').addEventListener('click', async (e) => {
      const btn = e.currentTarget;
      const slug = item.slug || item.project_id;
      const projectType = item.project_type || 'mod';

      btn.disabled = true;
      btn.style.opacity = '0.7';
      btn.innerHTML = `<div class="btn-spinner" style="width:14px;height:14px;border-width:2.5px;"></div> <span>Installing...</span>`;

      openInstallProgressModal(item.title, projectType);

      if (window.pywebview && window.pywebview.api) {
        try {
          if (window.pywebview.api.start_package_install) {
            await window.pywebview.api.start_package_install(slug, projectType);
            startPollingInstallProgress();
          } else if (window.pywebview.api.install_package) {
            const res = await window.pywebview.api.install_package(slug, projectType);
            if (res && res.success) {
              showToast(`✓ Successfully installed ${res.title || slug}!`);
              closeInstallProgressModal();
              if (typeof reloadLauncherState === 'function') await reloadLauncherState();
              if (projectType === 'mod' && typeof loadMods === 'function') {
                await loadMods();
              }
            } else {
              showToast(`Install failed: ${res && res.error ? res.error : 'Error'}`);
            }
          }
        } catch (err) {
          showToast(`Install exception: ${err.message || err}`);
        }
      } else {
        showToast('Installing ' + slug);
      }
    });

    // External link handler
    card.querySelector('.btn-external-link').addEventListener('click', (e) => {
      const url = e.currentTarget.dataset.url;
      if (window.pywebview && window.pywebview.api && window.pywebview.api.open_external_url) {
        window.pywebview.api.open_external_url(url);
      } else {
        window.open(url, '_blank');
      }
    });

    grid.appendChild(card);
  });
}

function renderCatalogPagination() {
  const container = document.getElementById('catalog-pagination-container');
  if (!container) return;
  const maxPage = Math.min(Math.max(1, Math.ceil(catalogTotalHits / catalogPageSize)), 500);

  if (maxPage <= 1) {
    container.innerHTML = '';
    return;
  }

  container.innerHTML = '';
  const paginationItems = getPaginationItems(catalogPage, maxPage);

  // Prev Button
  const prevBtn = document.createElement('button');
  prevBtn.className = 'page-btn';
  prevBtn.disabled = catalogPage <= 1;
  prevBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"/></svg>`;
  prevBtn.title = 'Previous Page';
  prevBtn.onclick = () => {
    if (catalogPage > 1) {
      catalogPage--;
      loadCatalog();
      document.getElementById('catalog-results-header')?.scrollIntoView({ behavior: 'smooth' });
    }
  };
  container.appendChild(prevBtn);

  // Numbered buttons
  paginationItems.forEach(item => {
    if (item === '...') {
      const dots = document.createElement('span');
      dots.className = 'page-dots';
      dots.innerText = '...';
      container.appendChild(dots);
    } else {
      const pageBtn = document.createElement('button');
      pageBtn.className = `page-btn ${item === catalogPage ? 'active' : ''}`;
      pageBtn.innerText = item;
      pageBtn.onclick = () => {
        if (item !== catalogPage) {
          catalogPage = item;
          loadCatalog();
          document.getElementById('catalog-results-header')?.scrollIntoView({ behavior: 'smooth' });
        }
      };
      container.appendChild(pageBtn);
    }
  });

  // Next Button
  const nextBtn = document.createElement('button');
  nextBtn.className = 'page-btn';
  nextBtn.disabled = catalogPage >= maxPage;
  nextBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="m9 18 6-6-6-6"/></svg>`;
  nextBtn.title = 'Next Page';
  nextBtn.onclick = () => {
    if (catalogPage < maxPage) {
      catalogPage++;
      loadCatalog();
      document.getElementById('catalog-results-header')?.scrollIntoView({ behavior: 'smooth' });
    }
  };
  container.appendChild(nextBtn);
}

// Search input with debounce
const inCatSearch = document.getElementById('catalog-search-input');
if (inCatSearch) {
  inCatSearch.addEventListener('input', (e) => {
    catalogQuery = e.target.value.trim();
    catalogPage = 1;
    clearTimeout(catalogSearchTimer);
    catalogSearchTimer = setTimeout(() => {
      loadCatalog();
    }, 400);
  });
  inCatSearch.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      clearTimeout(catalogSearchTimer);
      loadCatalog();
    }
  });
}

// Category filter tabs
document.querySelectorAll('#catalog-category-filters .catalog-cat-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('#catalog-category-filters .catalog-cat-btn').forEach(b => {
      b.className = 'btn btn-white catalog-cat-btn';
    });
    btn.className = 'btn btn-peri catalog-cat-btn';
    catalogType = btn.dataset.type;
    catalogPage = 1;
    loadCatalog();
  });
});

// Sort Dropdown interaction
const sortBtn = document.getElementById('catalog-sort-btn');
const sortMenu = document.getElementById('catalog-sort-menu');
const sortLabel = document.getElementById('catalog-sort-label');
const sortChevron = document.getElementById('catalog-sort-chevron');

if (sortBtn && sortMenu) {
  sortBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    const isOpen = sortMenu.style.display === 'flex';
    sortMenu.style.display = isOpen ? 'none' : 'flex';
    if (sortChevron) sortChevron.style.transform = isOpen ? 'none' : 'rotate(180deg)';
  });

  document.addEventListener('click', () => {
    if (sortMenu) sortMenu.style.display = 'none';
    if (sortChevron) sortChevron.style.transform = 'none';
  });

  sortMenu.querySelectorAll('.tactile-dropdown-item').forEach(item => {
    item.addEventListener('click', () => {
      catalogSort = item.dataset.sort;
      if (sortLabel) sortLabel.innerText = sortLabels[catalogSort] || 'Most Relevant';
      sortMenu.querySelectorAll('.tactile-dropdown-item').forEach(i => {
        i.classList.remove('active');
        i.innerHTML = `<span>${sortLabels[i.dataset.sort]}</span>`;
      });
      item.classList.add('active');
      item.innerHTML = `<span>${sortLabels[catalogSort]}</span><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`;
      sortMenu.style.display = 'none';
      if (sortChevron) sortChevron.style.transform = 'none';
      catalogPage = 1;
      loadCatalog();
    });
  });
}


// ==========================================
// VIEW 4: SERVERS & MULTIPLAYER STUDIO
// ==========================================
async function loadServers() {
  const container = document.getElementById('servers-list-container');
  if (!container) return;
  container.innerHTML = '<div style="text-align: center; padding: 25px; font-weight: 700; color: var(--ink-muted);">Pinging favorite servers with socket TCP...</div>';

  let servers = [];
  if (window.pywebview && window.pywebview.api) {
    try {
      const res = await window.pywebview.api.get_servers();
      servers = res.servers || [];
    } catch (e) {
      console.error(e);
    }
  } else {
    servers = [
      {
        name: 'CubeCraft Games',
        address: 'play.cubecraft.net:25565',
        category: 'Survival & Bedwars',
        ping: { online: true, latency: 162, motd: 'CubeCraft Network', players_online: 495, players_max: 5000 }
      },
      {
        name: 'Hypixel Network',
        address: 'mc.hypixel.net:25565',
        category: 'Minigames',
        ping: { online: false, latency: 0, motd: 'Offline', players_online: 0, players_max: 0 }
      }
    ];
  }

  renderServersList(servers);
}

function renderServersList(servers) {
  const container = document.getElementById('servers-list-container');
  if (!container) return;
  container.innerHTML = '';

  if (!servers.length) {
    container.innerHTML = '<div style="text-align: center; padding: 30px; font-weight: 700; color: var(--ink-muted);">No saved servers. Click "Add Server" to add your SMP!</div>';
    return;
  }

  servers.forEach(s => {
    const card = document.createElement('div');
    card.className = 'server-card-box';
    const isOnline = s.ping && s.ping.online;
    const lat = s.ping ? s.ping.latency : 0;
    const pOnline = s.ping ? s.ping.players_online : 0;
    const pMax = s.ping ? s.ping.players_max : 0;

    card.innerHTML = `
      <div>
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px;">
          <div>
            <div style="display: flex; align-items: center; gap: 8px;">
              <span class="ping-dot ${isOnline ? 'online' : 'offline'}"></span>
              <h4 style="font-size: 1.15rem; font-weight: 900;">${s.name}</h4>
            </div>
            <span style="font-family: var(--font-mono); font-size: 0.82rem; color: var(--ink-muted); margin-left: 18px;">${s.address}</span>
          </div>
          <div style="display: flex; gap: 6px;">
            ${isOnline ? `<span class="badge-tag" style="background: var(--pal-mint);">${lat} ms</span>` : '<span class="badge-tag" style="background: var(--pal-coral);">OFFLINE</span>'}
            ${isOnline ? `<span class="badge-tag" style="background: #ffffff;">${pOnline}/${pMax}</span>` : ''}
          </div>
        </div>
        <p style="font-size: 0.84rem; color: var(--ink-secondary); font-weight: 600; margin-left: 18px; margin-top: 4px;">
          ${s.ping && s.ping.motd ? s.ping.motd : 'Minecraft Multiplayer World'}
        </p>
      </div>

      <div style="display: flex; gap: 8px;">
        <button class="btn btn-primary btn-direct-play" data-addr="${s.address}" style="flex: 1; padding: 8px; font-size: 0.88rem;">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" stroke="none"><polygon points="5 3 19 12 5 21 5 3"/></svg>
          <span>Direct Connect & Play</span>
        </button>
        <button class="btn btn-secondary btn-del-server" data-name="${s.name}" title="Remove Server" style="padding: 8px 12px;">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
        </button>
      </div>
    `;

    // Direct connect
    card.querySelector('.btn-direct-play').addEventListener('click', () => {
      launchGame(s.address);
    });

    // Delete server
    card.querySelector('.btn-del-server').addEventListener('click', async () => {
      if (confirm(`Remove '${s.name}' from favorite servers?`)) {
        if (window.pywebview && window.pywebview.api) {
          await window.pywebview.api.delete_server(s.name);
          showToast('Server removed: ' + s.name);
          loadServers();
        }
      }
    });

    container.appendChild(card);
  });
}

// Refresh Servers
const btnServRef = document.getElementById('btn-servers-refresh');
if (btnServRef) btnServRef.addEventListener('click', () => loadServers());

// Launch Host Tunnel
const btnHost = document.getElementById('btn-launch-host-tunnel');
if (btnHost) {
  btnHost.addEventListener('click', () => {
    if (window.pywebview && window.pywebview.api) {
      window.pywebview.api.start_host_tunnel();
      showToast('Opened Host World Tunnel console');
    }
  });
}

// Copy Invite Link
const btnCopyInvite = document.getElementById('btn-copy-invite-link');
if (btnCopyInvite) {
  btnCopyInvite.addEventListener('click', () => {
    const username = appState.config ? appState.config.username || 'Player' : 'Player';
    const ver = appState.active_version || '1.20.1';
    const link = `moon://invite?user=${encodeURIComponent(username)}&version=${encodeURIComponent(ver)}`;
    navigator.clipboard.writeText(link).then(() => {
      showToast('Copied friend invite link: ' + link);
    }).catch(() => {
      showToast('Invite link: ' + link);
    });
  });
}

// Add Friend by Moon ID or Username
const btnFriendAdd = document.getElementById('btn-friend-add');
const inFriendAdd = document.getElementById('input-friend-add');
if (btnFriendAdd && inFriendAdd) {
  const submitAddFriend = async () => {
    const val = inFriendAdd.value.trim();
    if (!val) return;
    if (window.pywebview && window.pywebview.api && window.pywebview.api.add_friend) {
      const res = await window.pywebview.api.add_friend(val);
      if (res && res.success) {
        showToast('Added friend: ' + val);
        inFriendAdd.value = '';
        const state = await window.pywebview.api.get_launcher_state();
        applyLauncherState(state);
      } else {
        showToast('Failed to add friend: ' + (res.error || 'Unknown'), true);
      }
    } else {
      showToast('Added friend: ' + val);
      inFriendAdd.value = '';
    }
  };
  btnFriendAdd.addEventListener('click', submitAddFriend);
  inFriendAdd.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') submitAddFriend();
  });
}

// Add Server Modal
const modalAddServ = document.getElementById('modal-add-server');
const btnOpenAddServ = document.getElementById('btn-open-add-server-modal');
const btnCloseAddServ = document.getElementById('btn-close-server-modal');
const btnCancelAddServ = document.getElementById('btn-cancel-add-server');
const btnConfirmAddServ = document.getElementById('btn-confirm-add-server');

if (btnOpenAddServ && modalAddServ) {
  btnOpenAddServ.addEventListener('click', () => modalAddServ.classList.add('active'));
}
if (btnCloseAddServ && modalAddServ) {
  btnCloseAddServ.addEventListener('click', () => modalAddServ.classList.remove('active'));
}
if (btnCancelAddServ && modalAddServ) {
  btnCancelAddServ.addEventListener('click', () => modalAddServ.classList.remove('active'));
}
if (btnConfirmAddServ && modalAddServ) {
  btnConfirmAddServ.addEventListener('click', async () => {
    const nameIn = document.getElementById('modal-server-name');
    const addrIn = document.getElementById('modal-server-addr');
    const name = nameIn ? nameIn.value.trim() : '';
    const addr = addrIn ? addrIn.value.trim() : '';
    if (!name || !addr) {
      showToast('Please enter both server name and address', true);
      return;
    }
    if (window.pywebview && window.pywebview.api) {
      await window.pywebview.api.add_server(name, addr);
      showToast('Added server: ' + name);
      modalAddServ.classList.remove('active');
      if (nameIn) nameIn.value = '';
      if (addrIn) addrIn.value = '';
      loadServers();
    }
  });
}

// ==========================================
// VIEW 5: CRASH DIAGNOSTICS & LOGS
// ==========================================
async function loadCrashDiagnostics() {
  const headEl = document.getElementById('crash-status-headline');
  const detailEl = document.getElementById('crash-status-detail');
  const remBox = document.getElementById('crash-remediation-box');
  const remText = document.getElementById('crash-remediation-text');

  if (window.pywebview && window.pywebview.api) {
    try {
      const diag = await window.pywebview.api.get_crash_diagnostics(appState.active_version);
      if (diag.has_crash) {
        if (headEl) headEl.innerHTML = `<span style="color: var(--pal-coral);">${diag.error_type || 'Crash Detected'}</span>`;
        if (detailEl) detailEl.innerText = `${diag.description || ''}
${diag.failure_message || ''}`;
        if (remBox && remText) {
          remBox.style.display = 'block';
          remText.innerText = Array.isArray(diag.remediation) ? diag.remediation.join('\n') : diag.remediation;
        }
      } else {
        if (headEl) headEl.innerHTML = `<span style="color: #059669;">Instance Healthy - No Crashes Recorded</span>`;
        if (detailEl) detailEl.innerText = `Moon Launcher checked latest logs and crash-reports for '${appState.active_version}'. Everything is running smoothly.`;
        if (remBox) remBox.style.display = 'none';
      }
    } catch (e) {
      if (headEl) headEl.innerText = 'Diagnostics error: ' + e;
    }
  } else {
    if (headEl) headEl.innerHTML = `<span style="color: #059669;">Instance Healthy (Browser Preview)</span>`;
    if (detailEl) detailEl.innerText = 'No crash reports found.';
  }
}

async function loadLatestLog() {
  const consoleEl = document.getElementById('log-console-view');
  if (!consoleEl) return;
  consoleEl.innerText = 'Scanning latest.log for ' + appState.active_version + '...';

  if (window.pywebview && window.pywebview.api) {
    try {
      const res = await window.pywebview.api.get_latest_log(appState.active_version, 250);
      const lines = res.lines || [];
      consoleEl.innerText = lines.join('\n');
      consoleEl.scrollTop = consoleEl.scrollHeight;
    } catch (e) {
      consoleEl.innerText = 'Error reading latest.log: ' + e;
    }
  } else {
    consoleEl.innerText = '[12:00:00] [main/INFO]: Loading Minecraft 1.20.1\n[12:00:01] [main/INFO]: Forge Mod Loader initialized successfully\n[12:00:02] [main/INFO]: Loaded 85 mods smoothly\n[12:00:03] [main/INFO]: Ready for launch!';
  }
}

// Crash & Log action buttons
const btnCrashRef = document.getElementById('btn-crash-refresh');
if (btnCrashRef) btnCrashRef.addEventListener('click', () => loadCrashDiagnostics());

const btnAutoFix = document.getElementById('btn-run-auto-fix');
if (btnAutoFix) {
  btnAutoFix.addEventListener('click', () => {
    if (window.pywebview && window.pywebview.api) {
      window.pywebview.api.run_auto_fix(appState.active_version);
      showToast('Opened Automated Preflight Repair');
    }
  });
}

const btnOpenCrashFold = document.getElementById('btn-open-crash-folder');
if (btnOpenCrashFold) btnOpenCrashFold.addEventListener('click', () => openFolder('crash'));

const btnOpenLogFold = document.getElementById('btn-open-log-folder');
if (btnOpenLogFold) btnOpenLogFold.addEventListener('click', () => openFolder('logs'));

const btnLogRef = document.getElementById('btn-refresh-log');
if (btnLogRef) btnLogRef.addEventListener('click', () => loadLatestLog());

const btnCopyLog = document.getElementById('btn-copy-log');
if (btnCopyLog) {
  btnCopyLog.addEventListener('click', () => {
    const text = document.getElementById('log-console-view').innerText;
    navigator.clipboard.writeText(text).then(() => {
      showToast('Copied log output to clipboard');
    });
  });
}

// ==========================================
// VIEW 6: SETTINGS & SYSTEM STUDIO
// ==========================================
const btnSaveAllSet = document.getElementById('btn-save-all-settings');
if (btnSaveAllSet) {
  btnSaveAllSet.addEventListener('click', async () => {
    const settings = {
      java_path: document.getElementById('setting-java-path').value.trim(),
      ram_max_gb: parseInt(document.getElementById('setting-ram-slider').value),
      width: parseInt(document.getElementById('setting-width').value) || 1280,
      height: parseInt(document.getElementById('setting-height').value) || 720,
      fullscreen: document.getElementById('setting-fullscreen').checked,
      discord_rpc: document.getElementById('setting-discord-rpc').checked,
      jvm_g1gc_preset: document.getElementById('setting-jvm-g1gc').checked
    };

    if (window.pywebview && window.pywebview.api) {
      await window.pywebview.api.save_settings(settings);
      showToast('Saved all configuration settings');
      const state = await window.pywebview.api.get_launcher_state();
      applyLauncherState(state);
    } else {
      showToast('Settings saved');
    }
  });
}

const setRamSlider = document.getElementById('setting-ram-slider');
const setRamLabel = document.getElementById('setting-ram-label');
if (setRamSlider && setRamLabel) {
  setRamSlider.addEventListener('input', (e) => {
    setRamLabel.innerText = e.target.value + ' GB';
  });
}

// Updater Studio
const btnCheckUp = document.getElementById('btn-check-updates');
if (btnCheckUp) {
  btnCheckUp.addEventListener('click', async () => {
    showToast('Checking GitHub for launcher updates...');
    if (window.pywebview && window.pywebview.api) {
      const res = await window.pywebview.api.check_updates();
      if (res && res.update_available) {
        showToast(`Update Available! (${res.latest_version || 'New patch'}) Click 'Update Now'!`);
      } else {
        showToast('Moon Launcher is up to date! (v2.4.5)');
      }
    }
  });
}

const btnRunUp = document.getElementById('btn-run-update');
if (btnRunUp) {
  btnRunUp.addEventListener('click', () => {
    if (window.pywebview && window.pywebview.api) {
      window.pywebview.api.run_launcher_update();
      showToast('Launcher update utility launched');
    }
  });
}

// ==========================================
// SKIN & CAPE CUSTOMIZER MODAL
// ==========================================
const modalSkin = document.getElementById('modal-skin-customizer');
const btnOpenSkin = document.getElementById('btn-open-skin-modal');
const btnCloseSkin = document.getElementById('btn-close-skin-modal');
const btnHeadChip = document.getElementById('header-player-chip');
const inSkin = document.getElementById('modal-skin-input');
const imgSkinPrev = document.getElementById('modal-skin-preview-img');
const btnSkinApply = document.getElementById('btn-skin-apply');
const btnSkinReset = document.getElementById('btn-skin-reset');
const dropzone = document.getElementById('skin-upload-dropzone');
const fileInput = document.getElementById('skin-file-input');
const btnTriggerPick = document.getElementById('btn-trigger-file-pick');
const lblSkinFile = document.getElementById('modal-skin-file-label');
const btnFetchPrev = document.getElementById('btn-fetch-skin-preview');

let stagedSkin = {
  type: 'none', // 'file_path', 'base64', 'url_or_name'
  data: '',
  filename: ''
};

function openSkinModal() {
  if (!modalSkin) return;
  modalSkin.classList.add('active');
  const u = appState.config ? appState.config.username || 'Player' : 'Player';
  const curSkin = (appState.config && appState.config.custom_skin) || '';
  if (inSkin) inSkin.value = curSkin.startsWith('http') ? curSkin : '';
  if (lblSkinFile) {
    if (curSkin && !curSkin.startsWith('http')) {
      lblSkinFile.innerText = 'Active file: ' + curSkin.split('\\').pop();
    } else {
      lblSkinFile.innerText = 'Select a .png skin file from your PC or paste link';
    }
  }
  if (imgSkinPrev) {
    imgSkinPrev.src = appState.avatar_url || 'https://minotar.net/bust/Steve/128.png';
  }
  stagedSkin = { type: 'none', data: '', filename: '' };
}

if (btnOpenSkin) btnOpenSkin.addEventListener('click', openSkinModal);
if (btnHeadChip) btnHeadChip.addEventListener('click', openSkinModal);
if (btnCloseSkin) btnCloseSkin.addEventListener('click', () => modalSkin.classList.remove('active'));

// Handle File Selection (Native Python or HTML Input)
async function triggerFilePicker() {
  // If pywebview has native choose_skin_file API
  if (window.pywebview && window.pywebview.api && window.pywebview.api.choose_skin_file) {
    try {
      const res = await window.pywebview.api.choose_skin_file();
      if (res && res.success) {
        stagedSkin = {
          type: 'file_path',
          data: res.path,
          filename: res.filename
        };
        if (imgSkinPrev && res.preview_url) {
          imgSkinPrev.src = res.preview_url;
        }
        if (lblSkinFile) {
          lblSkinFile.innerText = 'Selected: ' + res.filename;
        }
        showToast('Loaded skin file: ' + res.filename);
        return;
      } else if (res && res.cancelled) {
        return;
      }
    } catch (e) {
      console.warn('Native picker fallback to html input:', e);
    }
  }

  // Fallback to HTML input file click
  if (fileInput) fileInput.click();
}

if (btnTriggerPick) {
  btnTriggerPick.addEventListener('click', (e) => {
    e.stopPropagation();
    triggerFilePicker();
  });
}

if (dropzone) {
  dropzone.addEventListener('click', () => triggerFilePicker());

  // Drag & drop handlers
  dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('dragover');
  });
  dropzone.addEventListener('dragleave', () => {
    dropzone.classList.remove('dragover');
  });
  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleHtmlFile(e.dataTransfer.files[0]);
    }
  });
}

if (fileInput) {
  fileInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleHtmlFile(e.target.files[0]);
    }
  });
}

function handleHtmlFile(file) {
  if (!file.name.toLowerCase().endsWith('.png')) {
    showToast('Please select a valid PNG image (.png)', true);
    return;
  }
  const reader = new FileReader();
  reader.onload = function(evt) {
    const rawDataUrl = evt.target.result;
    
    // Extract 128x128 head composite on client-side canvas
    const tempImg = new Image();
    tempImg.onload = function() {
      let previewHeadUrl = rawDataUrl;
      try {
        const canvas = document.createElement('canvas');
        canvas.width = 128;
        canvas.height = 128;
        const ctx = canvas.getContext('2d');
        ctx.imageSmoothingEnabled = false;
        
        const w = tempImg.naturalWidth || tempImg.width || 64;
        const scale = Math.max(1, Math.floor(w / 64));
        
        // Face (8x8)
        ctx.drawImage(tempImg, 8 * scale, 8 * scale, 8 * scale, 8 * scale, 0, 0, 128, 128);
        // Outer hat/hair
        ctx.drawImage(tempImg, 40 * scale, 8 * scale, 8 * scale, 8 * scale, 0, 0, 128, 128);
        
        previewHeadUrl = canvas.toDataURL('image/png');
      } catch (err) {
        console.warn('Canvas head extraction fallback:', err);
      }
      
      stagedSkin = {
        type: 'base64',
        data: rawDataUrl,
        preview_url: previewHeadUrl,
        filename: file.name
      };
      
      if (imgSkinPrev) imgSkinPrev.src = previewHeadUrl;
      if (lblSkinFile) lblSkinFile.innerText = 'Selected: ' + file.name;
      showToast('Skin loaded: ' + file.name);
    };
    tempImg.src = rawDataUrl;
  };
  reader.readAsDataURL(file);
}

// Fetch preview for manual URL or username input
function updateManualPreview() {
  const val = inSkin ? inSkin.value.trim() : '';
  if (!val) return;
  stagedSkin = {
    type: 'url_or_name',
    data: val,
    filename: val
  };
  if (val.startsWith('http://') || val.startsWith('https://')) {
    if (imgSkinPrev) imgSkinPrev.src = val;
    if (lblSkinFile) lblSkinFile.innerText = 'URL: ' + val.split('/').pop();
  } else if (val.toLowerCase() !== 'auto') {
    if (imgSkinPrev) imgSkinPrev.src = `https://minotar.net/bust/${encodeURIComponent(val)}/128.png`;
    if (lblSkinFile) lblSkinFile.innerText = 'Player: ' + val;
  }
}

if (btnFetchPrev) btnFetchPrev.addEventListener('click', updateManualPreview);
if (inSkin) {
  inSkin.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') updateManualPreview();
  });
}

// Apply Staged Skin
if (btnSkinApply) {
  btnSkinApply.addEventListener('click', async () => {
    // If user typed into the input but hasn't staged yet
    if (stagedSkin.type === 'none') {
      const manualVal = inSkin ? inSkin.value.trim() : '';
      if (manualVal) {
        stagedSkin = { type: 'url_or_name', data: manualVal, filename: manualVal };
      } else {
        showToast('Please choose a skin file (.png) or type a username/link', true);
        return;
      }
    }

    showToast('Applying skin to Minecraft profile...');

    if (window.pywebview && window.pywebview.api) {
      try {
        let res;
        if (stagedSkin.type === 'base64') {
          res = await window.pywebview.api.apply_skin_data(stagedSkin.filename, stagedSkin.data);
        } else {
          res = await window.pywebview.api.apply_skin(stagedSkin.data);
        }
        showToast('Skin applied successfully & broadcast to LAN!');
        modalSkin.classList.remove('active');

        // Immediately update avatar images if returned
        if (res && res.avatar_url) {
          const headAvatar = document.getElementById('header-avatar-img');
          if (headAvatar) headAvatar.src = res.avatar_url;
          const dashAvatar = document.getElementById('dash-avatar-bust');
          if (dashAvatar) dashAvatar.src = res.avatar_url;
          appState.avatar_url = res.avatar_url;
        }

        // Re-fetch entire state from backend
        const state = await window.pywebview.api.get_launcher_state();
        applyLauncherState(state);
      } catch (err) {
        showToast('Error applying skin: ' + err, true);
      }
    } else {
      showToast('Skin applied (Browser Preview Mode)');
      modalSkin.classList.remove('active');
    }
  });
}

// Reset Skin to Auto
if (btnSkinReset) {
  btnSkinReset.addEventListener('click', async () => {
    if (window.pywebview && window.pywebview.api) {
      await window.pywebview.api.apply_skin('auto');
      showToast('Skin reset to default player avatar');
      modalSkin.classList.remove('active');
      const state = await window.pywebview.api.get_launcher_state();
      applyLauncherState(state);
    }
  });
}


// Modal Install Buttons Binding
const btnCloseInstall = document.getElementById('btn-close-install-modal');
if (btnCloseInstall) btnCloseInstall.addEventListener('click', closeInstallProgressModal);

const btnMinInstall = document.getElementById('btn-minimize-install-modal');
if (btnMinInstall) btnMinInstall.addEventListener('click', closeInstallProgressModal);

const btnFinishInstall = document.getElementById('btn-finish-install-modal');
if (btnFinishInstall) {
  btnFinishInstall.addEventListener('click', async () => {
    closeInstallProgressModal();
    const verName = (lastInstalledResult && (lastInstalledResult.version_name || lastInstalledResult.title))
      ? (lastInstalledResult.version_name || lastInstalledResult.title)
      : null;
    const pType = (lastInstalledResult && lastInstalledResult.type) ? lastInstalledResult.type : 'modpack';

    if (verName && (pType === 'modpack' || pType === 'package')) {
      if (typeof switchVersion === 'function') {
        await switchVersion(verName);
      } else if (window.pywebview && window.pywebview.api && window.pywebview.api.set_active_version) {
        await window.pywebview.api.set_active_version(verName);
        if (typeof reloadLauncherState === 'function') await reloadLauncherState();
      }
    } else {
      if (typeof reloadLauncherState === 'function') await reloadLauncherState();
    }

    const playTab = document.querySelector('[data-tab="view-play"]');
    if (playTab) playTab.click();
  });
}


// ==============================================================================
// MODPACK LIVE SHARING & CODE IMPORT ENGINE (MOON-PACK-XXXX)
// ==============================================================================

let sharePollTimer = null;
let currentAllVersions = [];

function openShareModal(preselectVer = null) {
  const modal = document.getElementById('modal-share-pack');
  if (!modal) return;
  modal.classList.add('active');

  const select = document.getElementById('share-select-instance');
  if (select) {
    select.innerHTML = '';
    const activeVer = (launcherState && launcherState.active_version) ? launcherState.active_version.name : '';
    const versions = (launcherState && launcherState.installed_versions) ? launcherState.installed_versions : [];
    currentAllVersions = versions;

    versions.forEach(v => {
      const opt = document.createElement('option');
      opt.value = v.name;
      opt.textContent = `${v.name} (${v.loader || 'Forge'} ${v.mc_version || '1.20.1'} - ${v.mod_count || 0} mods)`;
      if (preselectVer && v.name === preselectVer) opt.selected = true;
      else if (!preselectVer && v.name === activeVer) opt.selected = true;
      select.appendChild(opt);
    });
  }

  // Check if already sharing
  checkActiveShareStatus();
}

function closeShareModal() {
  const modal = document.getElementById('modal-share-pack');
  if (modal) modal.classList.remove('active');
  if (sharePollTimer) {
    clearInterval(sharePollTimer);
    sharePollTimer = null;
  }
}

async function checkActiveShareStatus() {
  if (!window.pywebview || !window.pywebview.api || !window.pywebview.api.get_pack_share_status) return;
  try {
    const st = await window.pywebview.api.get_pack_share_status();
    const vSetup = document.getElementById('share-view-setup');
    const vActive = document.getElementById('share-view-active');

    if (st && st.running) {
      if (vSetup) vSetup.style.display = 'none';
      if (vActive) vActive.style.display = 'flex';

      const codeEl = document.getElementById('share-active-code');
      if (codeEl) codeEl.textContent = st.code || 'MOON-PACK-XXXX';

      const nameEl = document.getElementById('share-status-pack-name');
      if (nameEl) nameEl.textContent = st.pack_name || '-';

      const metaEl = document.getElementById('share-status-pack-meta');
      if (metaEl) metaEl.textContent = `${st.loader || 'Forge'} ${st.mc_version || '1.20.1'} • ${st.mod_count || 0} Mods`;

      const sizeEl = document.getElementById('share-status-pack-size');
      if (sizeEl) sizeEl.textContent = `${(st.size_bytes / (1024 * 1024)).toFixed(1)} MB`;

      const liveEl = document.getElementById('share-status-live');
      if (liveEl) {
        const sentMb = (st.bytes_sent / (1024 * 1024)).toFixed(1);
        const peers = st.active_downloads || 0;
        liveEl.innerHTML = peers > 0
          ? `<span style="color:#22c55e;">🚀 Mengirim data ke ${peers} teman... (${sentMb} MB terkirim)</span>`
          : `🟢 Siap Mengirim (${sentMb} MB total terkirim)`;
      }

      if (!sharePollTimer) {
        sharePollTimer = setInterval(checkActiveShareStatus, 2000);
      }
    } else {
      if (vSetup) vSetup.style.display = 'flex';
      if (vActive) vActive.style.display = 'none';
      if (sharePollTimer) {
        clearInterval(sharePollTimer);
        sharePollTimer = null;
      }
    }
  } catch (e) {
    console.error('Error checking share status:', e);
  }
}

async function startSharingSelectedPack() {
  const select = document.getElementById('share-select-instance');
  const verName = select ? select.value : '';
  if (!verName) {
    showToast('Pilih modpack terlebih dahulu', true);
    return;
  }

  const btnStart = document.getElementById('btn-start-sharing');
  const btnText = document.getElementById('btn-start-sharing-text');
  const oldText = btnText ? btnText.textContent : 'Buat Kode & Mulai Berbagi';

  try {
    if (btnStart) btnStart.disabled = true;
    if (btnText) btnText.textContent = 'Mengompres Modpack & Membuka Tunnel...';

    if (window.pywebview && window.pywebview.api && window.pywebview.api.start_pack_share) {
      const res = await window.pywebview.api.start_pack_share(verName);
      if (res && res.success) {
        showToast(`Berbagi dimulai! Kode: ${res.code}`);
        await checkActiveShareStatus();
      } else {
        showToast(`Gagal memulai: ${res ? res.error : 'Unknown error'}`, true);
      }
    }
  } catch (e) {
    showToast(`Error: ${e}`, true);
  } finally {
    if (btnStart) btnStart.disabled = false;
    if (btnText) btnText.textContent = oldText;
  }
}

async function stopSharingActivePack() {
  if (window.pywebview && window.pywebview.api && window.pywebview.api.stop_pack_share) {
    try {
      await window.pywebview.api.stop_pack_share();
      showToast('Berbagi modpack dihentikan.');
      await checkActiveShareStatus();
    } catch (e) {
      showToast(`Error: ${e}`, true);
    }
  }
}

function openImportModal() {
  const modal = document.getElementById('modal-import-pack');
  if (!modal) return;
  modal.classList.add('active');

  const input = document.getElementById('input-import-pack-code');
  if (input) {
    input.value = '';
    setTimeout(() => input.focus(), 100);
  }

  const prev = document.getElementById('import-pack-preview');
  if (prev) prev.style.display = 'none';

  const errEl = document.getElementById('import-pack-error');
  if (errEl) errEl.style.display = 'none';
}

function closeImportModal() {
  const modal = document.getElementById('modal-import-pack');
  if (modal) modal.classList.remove('active');
}

async function submitImportPack() {
  const input = document.getElementById('input-import-pack-code');
  const rawCode = input ? input.value.trim() : '';
  if (!rawCode) {
    showToast('Masukkan kode modpack terlebih dahulu!', true);
    return;
  }

  const btn = document.getElementById('btn-submit-import-pack');
  const btnTxt = document.getElementById('btn-submit-import-text');
  const errEl = document.getElementById('import-pack-error');
  const prevEl = document.getElementById('import-pack-preview');

  if (errEl) errEl.style.display = 'none';

  // Format code
  let cleanCode = rawCode.toUpperCase().replace(/\s+/g, '-');
  if (/^\d{4,6}$/.test(cleanCode)) cleanCode = `MOON-PACK-${cleanCode}`;
  else if (cleanCode.startsWith('PACK-')) cleanCode = `MOON-${cleanCode}`;

  try {
    if (btn) btn.disabled = true;
    if (btnTxt) btnTxt.textContent = 'Mencari di Cloud...';

    // 1. Resolve preview first
    if (window.pywebview && window.pywebview.api && window.pywebview.api.resolve_pack_code) {
      const res = await window.pywebview.api.resolve_pack_code(cleanCode);
      if (!res || !res.found) {
        if (errEl) {
          errEl.textContent = res ? res.error : 'Kode tidak ditemukan atau host offline.';
          errEl.style.display = 'block';
        }
        if (btn) btn.disabled = false;
        if (btnTxt) btnTxt.textContent = 'Download & Pasang';
        return;
      }

      // Show preview briefly
      if (prevEl) {
        const nameEl = document.getElementById('import-preview-name');
        if (nameEl) nameEl.textContent = res.pack_name || cleanCode;
        const metaEl = document.getElementById('import-preview-meta');
        if (metaEl) metaEl.textContent = `${res.loader || 'Forge'} ${res.mc_version || '1.20.1'} • ${res.mod_count || 0} Mods`;
        const hostEl = document.getElementById('import-preview-host');
        if (hostEl) hostEl.textContent = `Dari: ${res.host_user || 'Teman'}`;
        prevEl.style.display = 'block';
      }

      // Close import modal and open full progress HUD
      closeImportModal();
      openInstallProgressModal(res.pack_name || cleanCode, 'modpack');

      // Start actual download & installation worker
      if (window.pywebview.api.import_pack_by_code) {
        await window.pywebview.api.import_pack_by_code(cleanCode);
      }
    }
  } catch (e) {
    if (errEl) {
      errEl.textContent = `Error: ${e}`;
      errEl.style.display = 'block';
    }
  } finally {
    if (btn) btn.disabled = false;
    if (btnTxt) btnTxt.textContent = 'Download & Pasang';
  }
}

// Bind Share & Import UI Events
document.addEventListener('DOMContentLoaded', () => {
  // Open Share Modal button in header
  const btnOpenShare = document.getElementById('btn-open-share-modal');
  if (btnOpenShare) btnOpenShare.addEventListener('click', () => openShareModal());

  // Close Share Modal buttons
  const btnCloseShare = document.getElementById('btn-close-share-modal');
  if (btnCloseShare) btnCloseShare.addEventListener('click', closeShareModal);

  const btnHideShare = document.getElementById('btn-hide-share-modal');
  if (btnHideShare) btnHideShare.addEventListener('click', closeShareModal);

  // Start Sharing Button
  const btnStartShare = document.getElementById('btn-start-sharing');
  if (btnStartShare) btnStartShare.addEventListener('click', startSharingSelectedPack);

  // Stop Sharing Button
  const btnStopShare = document.getElementById('btn-stop-sharing');
  if (btnStopShare) btnStopShare.addEventListener('click', stopSharingActivePack);

  // Copy Code Button
  const btnCopyCode = document.getElementById('btn-copy-share-code');
  if (btnCopyCode) {
    btnCopyCode.addEventListener('click', () => {
      const codeEl = document.getElementById('share-active-code');
      const code = codeEl ? codeEl.textContent.trim() : '';
      if (code) {
        navigator.clipboard.writeText(code).then(() => {
          const txt = document.getElementById('btn-copy-share-code-text');
          if (txt) {
            const old = txt.textContent;
            txt.textContent = '✓ Tersalin!';
            setTimeout(() => { txt.textContent = old; }, 2000);
          }
          showToast(`Kode ${code} disalin ke clipboard!`);
        });
      }
    });
  }

  // Open Import Modal button in header
  const btnOpenImport = document.getElementById('btn-open-import-modal');
  if (btnOpenImport) btnOpenImport.addEventListener('click', openImportModal);

  // Close Import Modal buttons
  const btnCloseImport = document.getElementById('btn-close-import-modal');
  if (btnCloseImport) btnCloseImport.addEventListener('click', closeImportModal);

  const btnCancelImport = document.getElementById('btn-cancel-import');
  if (btnCancelImport) btnCancelImport.addEventListener('click', closeImportModal);

  // Submit Import
  const btnSubmitImport = document.getElementById('btn-submit-import-pack');
  if (btnSubmitImport) btnSubmitImport.addEventListener('click', submitImportPack);

  const inputImportCode = document.getElementById('input-import-pack-code');
  if (inputImportCode) {
    inputImportCode.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        submitImportPack();
      }
    });
  }
});
