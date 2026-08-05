/* admin.js — user & role management, traffic model calibration */

(() => {
  const $ = (id) => document.getElementById(id);

  $('btn-theme').onclick = () => {
    const cur = document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
    const next = cur === 'light' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
  };

  const HIGHWAY_TYPES = ['motorway', 'trunk', 'primary', 'secondary', 'tertiary', 'residential', 'unclassified'];
  const HOURS = Array.from({ length: 24 }, (_, i) => i);

  // ─── Users ──────────────────────────────────────────────────
  const usersBody   = $('users-body');
  const userStatus  = $('user-status');

  function renderUsers(users) {
    usersBody.innerHTML = '';
    for (const u of users) {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${u.username}</td>
        <td>
          <select data-id="${u.id}" class="role-select">
            <option value="planner"${u.role === 'planner' ? ' selected' : ''}>planner</option>
            <option value="admin"${u.role === 'admin' ? ' selected' : ''}>admin</option>
          </select>
        </td>
        <td>${new Date(u.created_at.replace(' ', 'T') + 'Z').toLocaleDateString()}</td>
        <td><button class="btn btn-ghost btn-delete-user" data-id="${u.id}">Delete</button></td>
      `;
      usersBody.appendChild(tr);
    }
  }

  function setStatus(el, message, kind) {
    el.textContent = message;
    el.className = 'status' + (kind ? ' ' + kind : '');
  }

  async function loadUsers() {
    try {
      renderUsers(await API.listUsers());
    } catch (e) {
      setStatus(userStatus, e.message, 'err');
    }
  }

  usersBody.addEventListener('change', async (ev) => {
    if (!ev.target.classList.contains('role-select')) return;
    try {
      await API.updateUser(ev.target.dataset.id, { role: ev.target.value });
      setStatus(userStatus, 'Role updated.', 'ok');
    } catch (e) {
      setStatus(userStatus, e.message, 'err');
      loadUsers();
    }
  });

  usersBody.addEventListener('click', async (ev) => {
    if (!ev.target.classList.contains('btn-delete-user')) return;
    if (!confirm('Delete this user?')) return;
    try {
      await API.deleteUser(ev.target.dataset.id);
      loadUsers();
    } catch (e) {
      setStatus(userStatus, e.message, 'err');
    }
  });

  $('form-add-user').addEventListener('submit', async (ev) => {
    ev.preventDefault();
    try {
      await API.createUser($('new-username').value.trim(), $('new-password').value, $('new-role').value);
      ev.target.reset();
      setStatus(userStatus, 'User created.', 'ok');
      loadUsers();
    } catch (e) {
      setStatus(userStatus, e.message, 'err');
    }
  });

  // ─── Traffic profile ────────────────────────────────────────
  const profileBody   = $('profile-body');
  const profileStatus = $('profile-status');

  function renderProfileHead() {
    $('profile-head').innerHTML = '<th>Road type</th>' + HOURS.map((h) => `<th>${h}</th>`).join('');
  }

  function renderProfile(profile) {
    profileBody.innerHTML = '';
    for (const hw of HIGHWAY_TYPES) {
      const tr = document.createElement('tr');
      const cells = (profile[hw] || []).map((v, hour) =>
        `<td><input type="number" min="0" max="1" step="0.01" value="${v}" data-hw="${hw}" data-hour="${hour}"></td>`
      ).join('');
      tr.innerHTML = `<td class="hw-label">${hw}</td>${cells}`;
      profileBody.appendChild(tr);
    }
  }

  async function loadProfile() {
    try {
      renderProfile(await API.getTrafficProfile());
    } catch (e) {
      setStatus(profileStatus, e.message, 'err');
    }
  }

  $('btn-save-profile').addEventListener('click', async () => {
    const next = {};
    for (const inp of profileBody.querySelectorAll('input')) {
      const hw = inp.dataset.hw;
      if (!next[hw]) next[hw] = new Array(24).fill(0);
      next[hw][Number(inp.dataset.hour)] = Number(inp.value);
    }
    try {
      renderProfile(await API.saveTrafficProfile(next));
      setStatus(profileStatus, 'Saved — predictions updated.', 'ok');
    } catch (e) {
      setStatus(profileStatus, e.message, 'err');
    }
  });

  $('btn-reset-profile').addEventListener('click', async () => {
    if (!confirm('Reset all road types to their default congestion values?')) return;
    try {
      renderProfile(await API.resetTrafficProfile());
      setStatus(profileStatus, 'Reset to defaults.', 'ok');
    } catch (e) {
      setStatus(profileStatus, e.message, 'err');
    }
  });

  renderProfileHead();
  loadUsers();
  loadProfile();
})();
