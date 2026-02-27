/**
 * Paper Agent — Web UI Controller
 *
 * Manages profiles, settings, and triggers GitHub Actions workflows
 * via the GitHub REST API. All secrets stored in localStorage only.
 */

// ── State ──
let config = null;
let editingProfileIndex = -1; // -1 = new profile

// ── LocalStorage Keys ──
const LS_OWNER = "pa_gh_owner";
const LS_REPO = "pa_gh_repo";
const LS_TOKEN = "pa_gh_token";

// ── Init ──
document.addEventListener("DOMContentLoaded", () => {
  loadGitHubConfig();
  loadConfigFromRepo();
});

// ════════════════════════════════════════════
//  GitHub Connection
// ════════════════════════════════════════════

function loadGitHubConfig() {
  document.getElementById("ghOwner").value = localStorage.getItem(LS_OWNER) || "";
  document.getElementById("ghRepo").value = localStorage.getItem(LS_REPO) || "";
  document.getElementById("ghToken").value = localStorage.getItem(LS_TOKEN) || "";
  updateConnectionStatus();
}

function saveGitHubConfig() {
  const owner = document.getElementById("ghOwner").value.trim();
  const repo = document.getElementById("ghRepo").value.trim();
  const token = document.getElementById("ghToken").value.trim();

  if (!owner || !repo || !token) {
    showToast("请填写所有 GitHub 连接信息");
    return;
  }

  localStorage.setItem(LS_OWNER, owner);
  localStorage.setItem(LS_REPO, repo);
  localStorage.setItem(LS_TOKEN, token);

  showToast("GitHub 配置已保存");
  updateConnectionStatus();
  loadConfigFromRepo();
}

function getGitHub() {
  return {
    owner: localStorage.getItem(LS_OWNER) || "",
    repo: localStorage.getItem(LS_REPO) || "",
    token: localStorage.getItem(LS_TOKEN) || "",
  };
}

function isConnected() {
  const gh = getGitHub();
  return gh.owner && gh.repo && gh.token;
}

function updateConnectionStatus() {
  const dot = document.querySelector(".dot");
  const text = document.querySelector(".status-text");
  if (isConnected()) {
    dot.classList.add("connected");
    text.textContent = "已连接";
  } else {
    dot.classList.remove("connected");
    text.textContent = "未连接";
  }
}

async function testConnection() {
  if (!isConnected()) {
    showToast("请先保存 GitHub 配置");
    return;
  }

  const gh = getGitHub();
  try {
    const resp = await fetch(`https://api.github.com/repos/${gh.owner}/${gh.repo}`, {
      headers: { Authorization: `Bearer ${gh.token}` },
    });
    if (resp.ok) {
      showToast("✅ 连接成功！");
      updateConnectionStatus();
    } else {
      const data = await resp.json();
      showToast(`❌ 连接失败: ${data.message || resp.status}`);
    }
  } catch (e) {
    showToast(`❌ 网络错误: ${e.message}`);
  }
}

function toggleTokenVisibility() {
  const input = document.getElementById("ghToken");
  input.type = input.type === "password" ? "text" : "password";
}

// ════════════════════════════════════════════
//  Config Loading / Saving via GitHub API
// ════════════════════════════════════════════

async function githubAPI(path, method = "GET", body = null) {
  const gh = getGitHub();
  const opts = {
    method,
    headers: {
      Authorization: `Bearer ${gh.token}`,
      Accept: "application/vnd.github.v3+json",
    },
  };
  if (body) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  const resp = await fetch(`https://api.github.com/repos/${gh.owner}/${gh.repo}${path}`, opts);
  return resp;
}

async function loadConfigFromRepo() {
  if (!isConnected()) return;

  try {
    const resp = await githubAPI("/contents/config.json");
    if (!resp.ok) {
      console.warn("Could not load config.json from repo");
      return;
    }
    const data = await resp.json();
    const raw = atob(data.content.replace(/\n/g, ""));
    const bytes = new Uint8Array([...raw].map(c => c.charCodeAt(0)));
    const content = new TextDecoder("utf-8").decode(bytes);
    config = JSON.parse(content);
    config._sha = data.sha; // needed for updates

    renderProfiles();
    renderSettings();
    populateProfileDropdown();
    showToast("配置已从 GitHub 加载");
  } catch (e) {
    console.error("Failed to load config:", e);
  }
}

async function saveConfigToRepo() {
  if (!isConnected() || !config) return;

  const gh = getGitHub();
  const sha = config._sha;
  const configCopy = { ...config };
  delete configCopy._sha;

  const jsonStr = JSON.stringify(configCopy, null, 2);
  const bytes = new TextEncoder().encode(jsonStr);
  const binary = String.fromCharCode(...bytes);
  const content = btoa(binary);

  try {
    const resp = await githubAPI("/contents/config.json", "PUT", {
      message: "📝 update config from web UI",
      content: content,
      sha: sha,
    });

    if (resp.ok) {
      const data = await resp.json();
      config._sha = data.content.sha;
      showToast("✅ 配置已保存到 GitHub");
    } else {
      const err = await resp.json();
      showToast(`❌ 保存失败: ${err.message || resp.status}`);
    }
  } catch (e) {
    showToast(`❌ 保存错误: ${e.message}`);
  }
}

// ════════════════════════════════════════════
//  Profiles Management
// ════════════════════════════════════════════

function renderProfiles() {
  const container = document.getElementById("profilesList");
  if (!config || !config.profiles || config.profiles.length === 0) {
    container.innerHTML = '<div class="empty-state">暂无 Profile，点击右上角添加</div>';
    return;
  }

  container.innerHTML = config.profiles
    .map((p, i) => {
      const dotClass = p.active ? "" : " inactive";
      const sources = (p.sources || []).join(", ");
      return `
      <div class="profile-item">
        <div class="profile-info">
          <div class="profile-name">
            <span class="profile-active-dot${dotClass}"></span>
            ${escHtml(p.name)}
          </div>
          <div class="profile-query">${escHtml(p.query)}</div>
          <div class="profile-meta">${escHtml(p.venue_filter)} · ${sources} · ${p.count || "auto"} 篇</div>
        </div>
        <div class="profile-actions">
          <button class="btn btn-outline btn-sm" onclick="editProfile(${i})">编辑</button>
          <button class="btn btn-danger btn-sm" onclick="deleteProfile(${i})">删除</button>
        </div>
      </div>`;
    })
    .join("");
}

function populateProfileDropdown() {
  const select = document.getElementById("pushProfile");
  select.innerHTML = '<option value="">全部 Active Profiles</option>';
  if (!config || !config.profiles) return;
  config.profiles.forEach((p) => {
    if (p.active) {
      const opt = document.createElement("option");
      opt.value = p.id;
      opt.textContent = p.name;
      select.appendChild(opt);
    }
  });
}

function openProfileModal(index = -1) {
  editingProfileIndex = index;
  const modal = document.getElementById("profileModal");
  const title = document.getElementById("modalTitle");

  if (index >= 0 && config && config.profiles[index]) {
    title.textContent = "编辑 Profile";
    const p = config.profiles[index];
    document.getElementById("modalId").value = p.id;
    document.getElementById("modalId").disabled = true;
    document.getElementById("modalName").value = p.name;
    document.getElementById("modalQuery").value = p.query;
    document.getElementById("modalSrcSS").checked = (p.sources || []).includes("semantic_scholar");
    document.getElementById("modalSrcOR").checked = (p.sources || []).includes("openreview");
    document.getElementById("modalSrcOA").checked = (p.sources || []).includes("openalex");
    document.getElementById("modalVenue").value = p.venue_filter || "any";
    document.getElementById("modalCount").value = p.count || "";
    document.getElementById("modalActive").checked = p.active !== false;
  } else {
    title.textContent = "添加 Profile";
    document.getElementById("modalId").value = "";
    document.getElementById("modalId").disabled = false;
    document.getElementById("modalName").value = "";
    document.getElementById("modalQuery").value = "";
    document.getElementById("modalSrcSS").checked = true;
    document.getElementById("modalSrcOR").checked = true;
    document.getElementById("modalSrcOA").checked = true;
    document.getElementById("modalVenue").value = "any";
    document.getElementById("modalCount").value = "";
    document.getElementById("modalActive").checked = true;
  }

  modal.classList.remove("hidden");
}

function closeProfileModal() {
  document.getElementById("profileModal").classList.add("hidden");
  editingProfileIndex = -1;
}

function saveProfile() {
  const id = document.getElementById("modalId").value.trim();
  const name = document.getElementById("modalName").value.trim();
  const query = document.getElementById("modalQuery").value.trim();

  if (!id || !name || !query) {
    showToast("请填写 ID、名称和搜索需求");
    return;
  }

  if (!/^[a-zA-Z0-9_]+$/.test(id)) {
    showToast("Profile ID 只能包含英文字母、数字和下划线");
    return;
  }

  const sources = [];
  if (document.getElementById("modalSrcSS").checked) sources.push("semantic_scholar");
  if (document.getElementById("modalSrcOR").checked) sources.push("openreview");
  if (document.getElementById("modalSrcOA").checked) sources.push("openalex");

  const countVal = document.getElementById("modalCount").value;
  const count = countVal ? parseInt(countVal) : null;

  const profile = {
    id,
    name,
    query,
    sources,
    venue_filter: document.getElementById("modalVenue").value,
    count,
    active: document.getElementById("modalActive").checked,
  };

  if (!config) config = { profiles: [], venue_groups: {}, global: {} };
  if (!config.profiles) config.profiles = [];

  if (editingProfileIndex >= 0) {
    config.profiles[editingProfileIndex] = profile;
  } else {
    // Check for duplicate ID
    if (config.profiles.some((p) => p.id === id)) {
      showToast("Profile ID 已存在");
      return;
    }
    config.profiles.push(profile);
  }

  closeProfileModal();
  renderProfiles();
  populateProfileDropdown();
  saveConfigToRepo();
}

function editProfile(index) {
  openProfileModal(index);
}

function deleteProfile(index) {
  if (!config || !config.profiles[index]) return;
  const name = config.profiles[index].name;
  if (!confirm(`确定删除 Profile "${name}"？`)) return;

  config.profiles.splice(index, 1);
  renderProfiles();
  populateProfileDropdown();
  saveConfigToRepo();
}

// ════════════════════════════════════════════
//  Settings
// ════════════════════════════════════════════

function renderSettings() {
  if (!config || !config.global) return;

  const g = config.global;
  document.getElementById("settEmail").value = g.email || "";
  document.getElementById("settTimezone").value = g.timezone || "America/Edmonton";

  if (g.schedule) {
    const days = g.schedule.days || [];
    document.getElementById("schedMon").checked = days.includes("monday");
    document.getElementById("schedTue").checked = days.includes("tuesday");
    document.getElementById("schedWed").checked = days.includes("wednesday");
    document.getElementById("schedThu").checked = days.includes("thursday");
    document.getElementById("schedFri").checked = days.includes("friday");
    document.getElementById("schedSat").checked = days.includes("saturday");
    document.getElementById("schedSun").checked = days.includes("sunday");

    const h = String(g.schedule.hour || 8).padStart(2, "0");
    const m = String(g.schedule.minute || 0).padStart(2, "0");
    document.getElementById("schedTime").value = `${h}:${m}`;
  }
}

function saveSettings() {
  if (!config) config = { profiles: [], venue_groups: {}, global: {} };
  if (!config.global) config.global = {};

  config.global.email = document.getElementById("settEmail").value.trim();
  config.global.timezone = document.getElementById("settTimezone").value;

  const days = [];
  if (document.getElementById("schedMon").checked) days.push("monday");
  if (document.getElementById("schedTue").checked) days.push("tuesday");
  if (document.getElementById("schedWed").checked) days.push("wednesday");
  if (document.getElementById("schedThu").checked) days.push("thursday");
  if (document.getElementById("schedFri").checked) days.push("friday");
  if (document.getElementById("schedSat").checked) days.push("saturday");
  if (document.getElementById("schedSun").checked) days.push("sunday");

  const timeVal = document.getElementById("schedTime").value;
  const [hour, minute] = timeVal.split(":").map(Number);

  config.global.schedule = { days, hour: hour || 8, minute: minute || 0 };

  saveConfigToRepo();
}

// ════════════════════════════════════════════
//  Push Trigger
// ════════════════════════════════════════════

async function triggerPush() {
  if (!isConnected()) {
    showToast("请先配置 GitHub 连接");
    return;
  }

  const gh = getGitHub();
  const profileId = document.getElementById("pushProfile").value;
  const query = document.getElementById("pushQuery").value.trim();
  const count = document.getElementById("pushCount").value;

  const statusEl = document.getElementById("pushStatus");
  statusEl.classList.remove("hidden", "success", "error");
  statusEl.classList.add("loading");
  statusEl.textContent = "⏳ 正在触发 workflow...";

  const inputs = {};
  if (query) inputs.query = query;
  if (profileId) inputs.profile = profileId;
  if (count) inputs.count = count;

  try {
    const resp = await fetch(
      `https://api.github.com/repos/${gh.owner}/${gh.repo}/actions/workflows/push.yml/dispatches`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${gh.token}`,
          Accept: "application/vnd.github.v3+json",
        },
        body: JSON.stringify({ ref: "main", inputs }),
      }
    );

    if (resp.status === 204) {
      statusEl.classList.remove("loading");
      statusEl.classList.add("success");
      statusEl.textContent = "✅ Workflow 已触发！论文推送将在几分钟内发送到你的邮箱。";
    } else {
      const data = await resp.json();
      statusEl.classList.remove("loading");
      statusEl.classList.add("error");
      statusEl.textContent = `❌ 触发失败: ${data.message || resp.status}`;
    }
  } catch (e) {
    statusEl.classList.remove("loading");
    statusEl.classList.add("error");
    statusEl.textContent = `❌ 网络错误: ${e.message}`;
  }
}

// ════════════════════════════════════════════
//  Utilities
// ════════════════════════════════════════════

function showToast(msg) {
  const toast = document.getElementById("toast");
  document.getElementById("toastMsg").textContent = msg;
  toast.classList.remove("hidden");
  toast.classList.add("visible");

  setTimeout(() => {
    toast.classList.remove("visible");
    setTimeout(() => toast.classList.add("hidden"), 300);
  }, 3000);
}

function escHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}
