/**
 * Paper Agent — Web UI Controller
 *
 * Two modes:
 * 1. Search Mode: Direct browser search via Semantic Scholar + OpenAlex + OpenReview
 *    → Shows results in page, export to markdown
 * 2. Push Mode: Configures scheduled GitHub Actions workflow
 *    → Weekly email push (5-10 papers with GPT summary)
 */

// ── State ──
let config = null;
let editingPushIndex = -1;
let editingSearchIndex = -1;
let searchResults = [];
let searchAbortController = null;
let currentLang = localStorage.getItem("pa_lang") || "zh";

// ── LocalStorage Keys ──
const LS_OWNER = "pa_gh_owner";
const LS_REPO = "pa_gh_repo";
const LS_TOKEN = "pa_gh_token";

const LS_OPENAI_KEY = "pa_openai_key";

// ════════════════════════════════════════
//  i18n — Internationalization
// ════════════════════════════════════════

const I18N = {
  zh: {
    mode_search: "搜索模式", mode_push: "推送模式",
    status_disconnected: "未连接", status_connected: "已连接",
    search_title: "🔍 论文搜索",
    hint_apikey: "(存储在浏览器本地，用于 GPT 解析查询)",
    label_search_query: '搜索查询 <span class="hint">(自然语言描述，GPT 会自动生成关键词组)</span>',
    ph_search_query: "例: 在建筑领域法规对比的chatbot/agent",
    label_keyword_groups: '关键词组 <span class="hint">(由 GPT 生成，也可手动编辑)</span>',
    ph_keyword_groups: "点击「生成关键词」由 GPT 自动填充，也可直接手动填写。每行一组，逗号分隔",
    btn_generate_kw: "🤖 生成关键词",
    label_venue: "Venue 分组",
    venue_any: "不限（Top venue 优先）",
    venue_any_short: "不限",
    label_max_per_group: "每组最大数量",
    label_year_from: "起始年份",
    ph_no_limit: "不限",
    btn_search: "开始搜索",
    btn_searching: "搜索中...",
    results_title: "📄 搜索结果",
    btn_export: "📥 导出 Markdown", btn_copy: "📋 复制",
    push_settings_title: "📬 推送设置",
    push_description: "选择要推送的 Profile，每周定时通过 GPT 生成中文摘要后发送到邮箱。如需更改推送内容，请编辑下方 Profile。",
    push_profiles_title: "📂 推送 Profiles",
    search_profiles_title: "📂 搜索 Profiles",
    btn_add: "+ 添加",
    settings_title: "⚙️ 设置",
    label_email: "📧 推送邮箱", label_timezone: "🕐 时区",
    label_summary_language: "📝 摘要语言",
    summary_lang_zh: "中文",
    summary_lang_en: "English",
    label_schedule: "📅 定时推送", label_push_time: "⏰ 推送时间",
    day_mon: "周一", day_tue: "周二", day_wed: "周三", day_thu: "周四",
    day_fri: "周五", day_sat: "周六", day_sun: "周日",
    btn_save_settings: "💾 保存设置",
    github_title: "🔑 GitHub 连接",
    hint_token: "(存储在浏览器本地)",
    btn_save_connect: "🔗 保存并连接", btn_test_connection: "测试连接",
    modal_add_push: "添加推送 Profile", modal_edit_push: "编辑推送 Profile",
    modal_add_search: "添加搜索 Profile", modal_edit_search: "编辑搜索 Profile",
    label_name: "名称",
    ph_push_name: "例: Construction + AI/ML 或 建筑法规Chatbot",
    label_push_query: '搜索需求 <span class="hint">(自然语言描述，GPT 会自动解析成关键词)</span>',
    ph_push_query: "例: 帮我找在建筑领域应用 LLM 做法规对比的论文",
    label_push_count: "每次推送数量",
    label_year_from_hint: '起始年份 <span class="hint">(只搜索该年份之后的论文)</span>',
    label_search_query_short: '搜索查询 <span class="hint">(自然语言描述)</span>',
    label_keyword_groups_short: "关键词组",
    ph_search_name: "例: Building Code + NLP 或 建筑法规检索",
    btn_generate_kw_from_query: "🤖 从查询生成关键词",
    btn_cancel: "取消", btn_save: "保存",
    // Dynamic strings used in JS
    toast_config_loaded: "配置已从 GitHub 加载",
    toast_config_saved: "✅ 配置已保存到 GitHub",
    toast_schedule_synced: "✅ 推送时间已同步到 GitHub Actions",
    toast_schedule_sync_fail: "⚠️ 推送时间同步失败，请手动检查 workflow 文件",
    toast_fill_name_query: "请填写名称和搜索需求",
    toast_fill_name_query_kw: "请填写名称，以及搜索查询或关键词组",
    toast_id_exists: "ID 已存在",
    toast_fill_query: "请先输入搜索查询",
    toast_fill_apikey: "请先填写 OpenAI API Key",
    toast_fill_query_or_kw: "请输入搜索查询或关键词组",
    toast_fill_github: "请填写所有 GitHub 连接信息",
    toast_generating_kw: "⏳ GPT 正在生成关键词组...",
    toast_kw_generated: "✅ 关键词组已生成，可手动编辑后搜索",
    toast_kw_modal_generating: "⏳ 正在生成关键词...",
    toast_kw_modal_done: "✅ 关键词已生成",
    toast_search_done: "✅ 搜索完成！找到 {0} 篇论文",
    toast_no_export: "没有可导出的结果",
    toast_exported: "✅ 已导出 {0} 篇论文",
    toast_no_copy: "没有可复制的结果",
    toast_copied: "✅ 已复制 {0} 篇论文到剪贴板",
    toast_copy_fail: "❌ 复制失败",
    toast_profile_loaded: '已加载搜索 Profile "{0}"',
    confirm_delete: '确定删除 "{0}"？',
    empty_push_profiles: "暂无推送 Profile，点击右上角添加",
    empty_search_profiles: "暂无搜索 Profile，点击右上角添加",
    empty_push_checklist: "暂无推送 Profile",
    profile_meta_per: "篇/次",
    checklist_each: "每次", checklist_unit: "篇",
    kw_groups_count: "{0} 组关键词",
    kw_groups_none: "无预设关键词（GPT 生成）",
    per_group_unit: "每组 {0} 篇",
    btn_search_icon: "🔍 搜索", btn_edit: "编辑", btn_delete: "删除",
    searching_group: "⏳ 搜索中... 关键词组 {0}/{1}: {2}",
  },
  en: {
    mode_search: "Search", mode_push: "Push",
    status_disconnected: "Disconnected", status_connected: "Connected",
    search_title: "🔍 Paper Search",
    hint_apikey: "(Stored locally, used for GPT query parsing)",
    label_search_query: 'Search Query <span class="hint">(Natural language, GPT auto-generates keyword groups)</span>',
    ph_search_query: "e.g. chatbot/agent for building code comparison",
    label_keyword_groups: 'Keyword Groups <span class="hint">(GPT-generated or manually edited)</span>',
    ph_keyword_groups: "Click 'Generate Keywords' for GPT auto-fill, or type manually. One group per line, comma-separated",
    btn_generate_kw: "🤖 Generate Keywords",
    label_venue: "Venue Group",
    venue_any: "Any (Top venues prioritized)",
    venue_any_short: "Any",
    label_max_per_group: "Max per Group",
    label_year_from: "Year From",
    ph_no_limit: "No limit",
    btn_search: "Search",
    btn_searching: "Searching...",
    results_title: "📄 Search Results",
    btn_export: "📥 Export Markdown", btn_copy: "📋 Copy",
    push_settings_title: "📬 Push Settings",
    push_description: "Select profiles to push. Papers are searched weekly, summarized by GPT, and sent to your email. Edit profiles below to change topics.",
    push_profiles_title: "📂 Push Profiles",
    search_profiles_title: "📂 Search Profiles",
    btn_add: "+ Add",
    settings_title: "⚙️ Settings",
    label_email: "📧 Email", label_timezone: "🕐 Timezone",
    label_summary_language: "📝 Summary Language",
    summary_lang_zh: "Chinese",
    summary_lang_en: "English",
    label_schedule: "📅 Schedule", label_push_time: "⏰ Push Time",
    day_mon: "Mon", day_tue: "Tue", day_wed: "Wed", day_thu: "Thu",
    day_fri: "Fri", day_sat: "Sat", day_sun: "Sun",
    btn_save_settings: "💾 Save Settings",
    github_title: "🔑 GitHub Connection",
    hint_token: "(Stored locally in browser)",
    btn_save_connect: "🔗 Save & Connect", btn_test_connection: "Test Connection",
    modal_add_push: "Add Push Profile", modal_edit_push: "Edit Push Profile",
    modal_add_search: "Add Search Profile", modal_edit_search: "Edit Search Profile",
    label_name: "Name",
    ph_push_name: "e.g. Construction + AI/ML",
    label_push_query: 'Search Description <span class="hint">(Natural language, GPT parses into keywords)</span>',
    ph_push_query: "e.g. Papers on LLM-based building code comparison",
    label_push_count: "Papers per Push",
    label_year_from_hint: 'Year From <span class="hint">(Only search papers after this year)</span>',
    label_search_query_short: 'Search Query <span class="hint">(Natural language)</span>',
    label_keyword_groups_short: "Keyword Groups",
    ph_search_name: "e.g. Building Code + NLP",
    btn_generate_kw_from_query: "🤖 Generate from Query",
    btn_cancel: "Cancel", btn_save: "Save",
    toast_config_loaded: "Config loaded from GitHub",
    toast_config_saved: "✅ Config saved to GitHub",
    toast_schedule_synced: "✅ Push schedule synced to GitHub Actions",
    toast_schedule_sync_fail: "⚠️ Schedule sync failed, please check workflow file manually",
    toast_fill_name_query: "Please fill in name and query",
    toast_fill_name_query_kw: "Please fill in name, and query or keyword groups",
    toast_id_exists: "ID already exists",
    toast_fill_query: "Please enter a search query first",
    toast_fill_apikey: "Please fill in your OpenAI API Key first",
    toast_fill_query_or_kw: "Please enter a query or keyword groups",
    toast_fill_github: "Please fill in all GitHub connection fields",
    toast_generating_kw: "⏳ GPT is generating keywords...",
    toast_kw_generated: "✅ Keywords generated, edit before searching",
    toast_kw_modal_generating: "⏳ Generating keywords...",
    toast_kw_modal_done: "✅ Keywords generated",
    toast_search_done: "✅ Search complete! Found {0} papers",
    toast_no_export: "No results to export",
    toast_exported: "✅ Exported {0} papers",
    toast_no_copy: "No results to copy",
    toast_copied: "✅ Copied {0} papers to clipboard",
    toast_copy_fail: "❌ Copy failed",
    toast_profile_loaded: 'Loaded search profile "{0}"',
    confirm_delete: 'Delete "{0}"?',
    empty_push_profiles: "No push profiles yet. Click + Add above.",
    empty_search_profiles: "No search profiles yet. Click + Add above.",
    empty_push_checklist: "No push profiles",
    profile_meta_per: "papers/push",
    checklist_each: "Each", checklist_unit: "papers",
    kw_groups_count: "{0} keyword groups",
    kw_groups_none: "No preset keywords (GPT-generated)",
    per_group_unit: "{0} per group",
    btn_search_icon: "🔍 Search", btn_edit: "Edit", btn_delete: "Delete",
    searching_group: "⏳ Searching... Group {0}/{1}: {2}",
  },
};

/** Get translated string, with optional {0},{1}... replacements */
function t(key, ...args) {
  let str = (I18N[currentLang] || I18N.zh)[key] || (I18N.zh)[key] || key;
  args.forEach((arg, i) => { str = str.replace(`{${i}}`, arg); });
  return str;
}

/** Apply translations to all elements with data-i18n attributes */
function applyI18n() {
  document.querySelectorAll("[data-i18n]").forEach(el => {
    const key = el.getAttribute("data-i18n");
    const val = (I18N[currentLang] || I18N.zh)[key];
    if (val) el.innerHTML = val;
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach(el => {
    const key = el.getAttribute("data-i18n-placeholder");
    const val = (I18N[currentLang] || I18N.zh)[key];
    if (val) el.placeholder = val;
  });
  // Update page title
  document.title = currentLang === "en"
    ? "Paper Agent — Academic Paper Console"
    : "Paper Agent — 学术论文推送控制台";
  // Update toggle button text
  document.getElementById("langToggle").textContent = currentLang === "zh" ? "EN" : "中文";
  // Re-render dynamic content
  if (config) {
    renderPushProfiles();
    renderSearchProfiles();
    renderPushChecklist();
  }
}

function toggleLang() {
  currentLang = currentLang === "zh" ? "en" : "zh";
  localStorage.setItem("pa_lang", currentLang);
  applyI18n();
}

// ── Init ──
document.addEventListener("DOMContentLoaded", () => {
  loadGitHubConfig();
  loadConfigFromRepo();
  document.getElementById("searchApiKey").value = localStorage.getItem(LS_OPENAI_KEY) || "";
  applyI18n();
});

// ════════════════════════════════════════
//  Mode Switching
// ════════════════════════════════════════

function switchMode(mode) {
  const searchPanel = document.getElementById("searchModePanel");
  const pushPanel = document.getElementById("pushModePanel");
  const searchProfiles = document.getElementById("searchProfilesPanel");
  const btnSearch = document.getElementById("btnModeSearch");
  const btnPush = document.getElementById("btnModePush");
  const pushOnlyPanels = document.querySelectorAll(".push-only-panel");

  if (mode === "search") {
    searchPanel.classList.remove("hidden");
    searchProfiles.classList.remove("hidden");
    pushPanel.classList.add("hidden");
    btnSearch.classList.add("active");
    btnPush.classList.remove("active");
    pushOnlyPanels.forEach(el => el.classList.add("hidden"));
  } else {
    searchPanel.classList.add("hidden");
    searchProfiles.classList.add("hidden");
    pushPanel.classList.remove("hidden");
    btnSearch.classList.remove("active");
    btnPush.classList.add("active");
    pushOnlyPanels.forEach(el => el.classList.remove("hidden"));
  }
}

// ════════════════════════════════════════
//  Direct Search (Browser-side)
// ════════════════════════════════════════

function saveSearchApiKey() {
  localStorage.setItem(LS_OPENAI_KEY, document.getElementById("searchApiKey").value.trim());
}

function toggleSearchKeyVisibility() {
  const input = document.getElementById("searchApiKey");
  input.type = input.type === "password" ? "text" : "password";
}

async function generateKeywords() {
  const query = document.getElementById("searchQuery").value.trim();
  const apiKey = localStorage.getItem(LS_OPENAI_KEY) || "";
  if (!query) { showToast(t("toast_fill_query")); return; }
  if (!apiKey) { showToast(t("toast_fill_apikey")); return; }

  const statusEl = document.getElementById("searchStatus");
  statusEl.classList.remove("hidden", "success", "error");
  statusEl.classList.add("loading");
  statusEl.textContent = t("toast_generating_kw");

  try {
    const resp = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Authorization": `Bearer ${apiKey}` },
      body: JSON.stringify({
        model: "gpt-5.4",
        messages: [
          { role: "system", content: GPT_KEYWORD_PROMPT },
          { role: "user", content: query },
        ],
        temperature: 0.3,
      }),
    });

    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.error?.message || `API error ${resp.status}`);
    }

    const data = await resp.json();
    const content = data.choices[0].message.content.trim();

    // Parse: expect one keyword group per line, comma-separated
    const kwArea = document.getElementById("searchKeywordGroups");
    kwArea.value = content;
    statusEl.classList.remove("loading");
    statusEl.classList.add("success");
    statusEl.textContent = t("toast_kw_generated");
  } catch (e) {
    statusEl.classList.remove("loading");
    statusEl.classList.add("error");
    statusEl.textContent = `❌ GPT 调用失败: ${e.message}`;
  }
}

const GPT_KEYWORD_PROMPT = `You are an academic search keyword generator. Given a user's research query (in any language), generate 6-10 groups of English search keywords optimized for academic APIs (Semantic Scholar, OpenAlex, OpenReview).

Rules:
- Output one keyword group per line
- Each group has 2-4 keywords separated by commas
- Keywords should be in English regardless of input language
- Cover different aspects/synonyms of the query for maximum recall
- Include domain-specific terms, method names, and broader alternatives
- First few groups should be most specific, later groups broader

Example input: "在建筑领域法规对比的chatbot/agent"
Example output:
building code, compliance checking, NLP
building regulation, chatbot, construction
automated code compliance, civil engineering
building code, LLM, agent
regulatory compliance, construction, AI
building code comparison, natural language processing
automated rule checking, building regulation
building code, question answering, construction
BIM, code compliance, NLP

Output ONLY the keyword groups, no explanations or numbering.`;

async function startSearch() {
  const query = document.getElementById("searchQuery").value.trim();
  const keywordGroupsRaw = document.getElementById("searchKeywordGroups").value.trim();
  const maxPerGroup = parseInt(document.getElementById("searchMaxResults").value) || 25;
  const yearFrom = parseInt(document.getElementById("searchYearFrom").value) || null;
  const venueFilter = document.getElementById("searchVenueFilter").value;

  if (!query && !keywordGroupsRaw) {
    showToast(t("toast_fill_query_or_kw"));
    return;
  }

  let keywordGroups = [];
  if (keywordGroupsRaw) {
    keywordGroups = keywordGroupsRaw.split("\n")
      .map(line => line.trim()).filter(line => line.length > 0)
      .map(line => line.split(",").map(kw => kw.trim()).filter(kw => kw));
  } else {
    keywordGroups = autoGenerateKeywordGroups(query);
  }

  const statusEl = document.getElementById("searchStatus");
  statusEl.classList.remove("hidden", "success", "error");
  statusEl.classList.add("loading");

  const btnSearch = document.getElementById("btnSearch");
  btnSearch.disabled = true;
  btnSearch.innerHTML = '<span class="btn-icon">⏳</span> ' + t('btn_searching');

  searchResults = [];
  const seenTitles = new Set();
  const resultsCard = document.getElementById("resultsCard");
  const resultsBody = document.getElementById("resultsBody");
  resultsBody.innerHTML = "";
  resultsCard.classList.remove("hidden");

  if (searchAbortController) searchAbortController.abort();
  searchAbortController = new AbortController();
  const signal = searchAbortController.signal;

  try {
    for (let gi = 0; gi < keywordGroups.length; gi++) {
      if (signal.aborted) break;
      const kws = keywordGroups[gi];
      const kwStr = kws.join(", ");
      statusEl.textContent = t('searching_group', gi + 1, keywordGroups.length, kwStr);

      // Search all three APIs in parallel
      const [s2Papers, oaPapers, orPapers] = await Promise.all([
        searchSemanticScholar(kws.join(" "), maxPerGroup, yearFrom, signal),
        searchOpenAlex(kws.join(" "), maxPerGroup, yearFrom, signal),
        searchOpenReview(kws.join(" "), maxPerGroup, signal),
      ]);

      const allPapers = [...s2Papers, ...oaPapers, ...orPapers];
      for (const paper of allPapers) {
        const normTitle = paper.title.toLowerCase().trim();
        if (!seenTitles.has(normTitle)) {
          seenTitles.add(normTitle);
          searchResults.push(paper);
        }
      }

      document.getElementById("resultCount").textContent = `${searchResults.length} papers`;
    }

    searchResults = scoreAndSort(searchResults, query, keywordGroups);
    searchResults = applyVenueFilter(searchResults, venueFilter);
    renderSearchResults(searchResults);

    statusEl.classList.remove("loading");
    statusEl.classList.add("success");
    statusEl.textContent = t('toast_search_done', searchResults.length);
  } catch (e) {
    if (e.name !== "AbortError") {
      statusEl.classList.remove("loading");
      statusEl.classList.add("error");
      statusEl.textContent = `❌ 搜索出错: ${e.message}`;
    }
  } finally {
    btnSearch.disabled = false;
    btnSearch.innerHTML = '<span class="btn-icon">🔍</span> ' + t('btn_search');
  }
}

function autoGenerateKeywordGroups(query) {
  const stopwords = new Set(["a","an","the","of","in","on","at","to","for","and","or","is","are","was","were","be","with","by","from","as","that","this","not","but","can","how","what","which"]);
  const words = query.split(/\s+/).filter(w => w.length > 2 && !stopwords.has(w.toLowerCase()));
  const groups = [];
  if (words.length >= 2) groups.push(words.slice(0, 5));
  if (words.length >= 4) groups.push(words.slice(0, 3));
  if (words.length >= 4) groups.push(words.slice(Math.floor(words.length / 2)));
  if (words.length >= 3) groups.push([words[0], words[words.length - 1]]);
  if (groups.length === 0) groups.push(words);
  return groups;
}

const VENUE_GROUPS = {
  top_cs_conference: ["ICLR", "NeurIPS", "ICML", "ACL", "EMNLP", "CVPR", "KDD", "AAAI"],
  top_construction_journal: [
    "Automation in Construction", "Advanced Engineering Informatics",
    "Journal of Computing in Civil Engineering", "Building and Environment",
    "Journal of Construction Engineering and Management", "Engineering Structures",
  ],
};

function applyVenueFilter(papers, venueFilter) {
  if (!venueFilter || venueFilter === "any") {
    // "any" mode: boost top venue papers to the front
    const allVenues = Object.values(VENUE_GROUPS).flat().map(v => v.toLowerCase());
    const isTop = p => p.venue && allVenues.some(v => p.venue.toLowerCase().includes(v) || v.includes(p.venue.toLowerCase()));
    const top = papers.filter(p => isTop(p));
    const rest = papers.filter(p => !isTop(p));
    return [...top, ...rest];
  }
  // Specific venue group: only keep papers matching that group
  const venues = (VENUE_GROUPS[venueFilter] || []).map(v => v.toLowerCase());
  if (!venues.length) return papers;
  return papers.filter(p =>
    p.venue && venues.some(v => p.venue.toLowerCase().includes(v) || v.includes(p.venue.toLowerCase()))
  );
}

// ── Semantic Scholar API ──

async function searchSemanticScholar(query, maxResults, yearFrom, signal) {
  const results = [];
  const params = new URLSearchParams({
    query, limit: Math.min(maxResults, 100).toString(),
    fields: "title,abstract,authors,venue,year,citationCount,externalIds,url",
  });
  if (yearFrom) params.set("year", `${yearFrom}-`);

  try {
    const resp = await fetch(`https://api.semanticscholar.org/graph/v1/paper/search?${params}`, { signal });
    if (resp.status === 429 || !resp.ok) return results;
    const data = await resp.json();
    for (const paper of (data.data || [])) {
      if (!paper.abstract) continue;
      let doi = (paper.externalIds || {}).DOI || null;
      let url = paper.url || (paper.paperId ? `https://www.semanticscholar.org/paper/${paper.paperId}` : "");
      results.push({
        title: paper.title || "", abstract: paper.abstract || "",
        authors: (paper.authors || []).map(a => a.name).filter(Boolean),
        venue: paper.venue || "", year: paper.year,
        citationCount: paper.citationCount, url, doi, source: "Semantic Scholar",
      });
      if (results.length >= maxResults) break;
    }
  } catch (e) { if (e.name !== "AbortError") console.warn("[S2]", e.message); }
  return results;
}

// ── OpenAlex API ──

async function searchOpenAlex(query, maxResults, yearFrom, signal) {
  const results = [];
  const filters = [`default.search:${query}`];
  if (yearFrom) filters.push(`from_publication_date:${yearFrom}-01-01`);
  const params = new URLSearchParams({
    filter: filters.join(","),
    per_page: Math.min(maxResults, 50).toString(),
    sort: "relevance_score:desc",
    mailto: "paperagent@example.com",
  });

  try {
    const resp = await fetch(`https://api.openalex.org/works?${params}`, { signal });
    if (!resp.ok) return results;
    const data = await resp.json();
    for (const work of (data.results || [])) {
      const abstract = reconstructAbstract(work.abstract_inverted_index);
      const title = work.title || "";
      if (!abstract || !title) continue;
      const loc = work.primary_location || {};
      const src = loc.source || {};
      const doi = work.doi || "";
      results.push({
        title, abstract,
        authors: (work.authorships || []).slice(0, 10).map(a => (a.author || {}).display_name).filter(Boolean),
        venue: src.display_name || "", year: work.publication_year,
        citationCount: work.cited_by_count,
        url: doi || work.id || "",
        doi: doi ? doi.replace("https://doi.org/", "") : null,
        source: "OpenAlex",
      });
      if (results.length >= maxResults) break;
    }
  } catch (e) { if (e.name !== "AbortError") console.warn("[OA]", e.message); }
  return results;
}

// ── OpenReview API ──

async function searchOpenReview(query, maxResults, signal) {
  const results = [];
  try {
    const params = new URLSearchParams({
      term: query,
      limit: Math.min(maxResults, 50).toString(),
      content: "all",
    });
    const resp = await fetch(`https://api2.openreview.net/notes/search?${params}`, { signal });
    if (!resp.ok) return results;
    const data = await resp.json();

    for (const note of (data.notes || [])) {
      const content = note.content || {};
      let title = content.title || {};
      if (typeof title === "object") title = title.value || "";
      let abstract = content.abstract || {};
      if (typeof abstract === "object") abstract = abstract.value || "";
      if (!title || !abstract) continue;

      let authorsData = content.authors || {};
      let authors = [];
      if (typeof authorsData === "object" && !Array.isArray(authorsData)) authors = authorsData.value || [];
      else if (Array.isArray(authorsData)) authors = authorsData;

      let noteVenue = content.venue || {};
      if (typeof noteVenue === "object") noteVenue = noteVenue.value || "";

      const forumId = note.forum || note.id || "";
      const url = forumId ? `https://openreview.net/forum?id=${forumId}` : "";

      let year = null;
      if (note.cdate) { try { year = new Date(note.cdate).getFullYear(); } catch(e) {} }
      if (!year) {
        const m = (note.invitation || "").match(/20[12]\d/);
        if (m) year = parseInt(m[0]);
      }

      results.push({
        title, abstract,
        authors: Array.isArray(authors) ? authors : [],
        venue: String(noteVenue || "OpenReview"),
        year, citationCount: null, url, doi: null,
        source: "OpenReview",
      });
      if (results.length >= maxResults) break;
    }
  } catch (e) { if (e.name !== "AbortError") console.warn("[OR]", e.message); }
  return results;
}

function reconstructAbstract(invertedIndex) {
  if (!invertedIndex) return "";
  const wp = [];
  for (const [word, positions] of Object.entries(invertedIndex)) {
    for (const pos of positions) wp.push([pos, word]);
  }
  wp.sort((a, b) => a[0] - b[0]);
  return wp.map(x => x[1]).join(" ");
}

// ── Relevance Scoring ──

function scoreAndSort(papers, query, keywordGroups) {
  const allTerms = new Set();
  for (const group of keywordGroups) {
    for (const kw of group) allTerms.add(kw.toLowerCase());
  }
  for (const w of (query || "").toLowerCase().split(/\s+/)) {
    if (w.length > 3) allTerms.add(w);
  }

  const scored = papers.map(paper => {
    const titleLower = paper.title.toLowerCase();
    const textLower = titleLower + " " + paper.abstract.toLowerCase();
    let score = 0;
    for (const term of allTerms) {
      if (textLower.includes(term)) {
        score += 1;
        if (titleLower.includes(term)) score += 2;
      }
    }
    if (paper.citationCount > 0) score += Math.min(Math.log10(paper.citationCount + 1), 3);
    return { ...paper, _score: score };
  });

  scored.sort((a, b) => b._score - a._score);
  return scored;
}

// ── Render Results ──

function renderSearchResults(papers) {
  const body = document.getElementById("resultsBody");
  document.getElementById("resultCount").textContent = `${papers.length} papers`;
  if (papers.length === 0) {
    body.innerHTML = '<div class="empty-state">未找到相关论文</div>';
    return;
  }
  body.innerHTML = papers.map((p, i) => {
    const authorStr = (p.authors || []).slice(0, 3).join(", ") + (p.authors && p.authors.length > 3 ? " et al." : "");
    const shortAbstract = truncateSentences(p.abstract, 3);
    return `
    <div class="result-item">
      <div class="result-number">${i + 1}</div>
      <div class="result-content">
        <div class="result-title"><a href="${escHtml(p.url)}" target="_blank" rel="noopener">${escHtml(p.title)}</a></div>
        <div class="result-meta">
          ${p.year ? `<span class="result-tag">${p.year}</span>` : ""}
          ${p.venue ? `<span class="result-tag venue">${escHtml(p.venue)}</span>` : ""}
          ${p.citationCount != null ? `<span>📊 ${p.citationCount}</span>` : ""}
          <span class="result-source">${escHtml(p.source)}</span>
        </div>
        <div class="result-authors">${escHtml(authorStr)}</div>
        <div class="result-abstract">${escHtml(shortAbstract)}</div>
      </div>
    </div>`;
  }).join("");
}

function truncateSentences(text, n) {
  if (!text) return "";
  const s = text.split(/(?<=[.!?])\s+/);
  return s.slice(0, n).join(" ") + (s.length > n ? "..." : "");
}

// ── Export ──

function exportMarkdown() {
  if (!searchResults.length) { showToast(t("toast_no_export")); return; }
  const query = document.getElementById("searchQuery").value.trim();
  const now = new Date();
  let md = `# Paper Agent Search Results — ${now.toISOString().slice(0,16).replace("T"," ")}\nQuery: ${query}\nTotal: ${searchResults.length} papers\n\n`;
  searchResults.forEach((p, i) => {
    md += `### ${i+1}. ${p.title}\n`;
    md += `**Year:** ${p.year||"N/A"} | **Venue:** ${p.venue||"N/A"} | **Citations:** ${p.citationCount??"N/A"} | **Source:** ${p.source}\n`;
    if (p.url) md += `**URL:** ${p.url}\n`;
    const a = (p.authors||[]).slice(0,5).join(", ") + (p.authors&&p.authors.length>5?" et al.":"");
    if (a) md += `**Authors:** ${a}\n`;
    md += `\n> ${truncateSentences(p.abstract,2)}\n\n`;
  });
  const blob = new Blob([md], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a"); a.href = url;
  a.download = `papers_${now.toISOString().slice(0,10)}.md`;
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  URL.revokeObjectURL(url);
  showToast(t('toast_exported', searchResults.length));
}

function copyResults() {
  if (!searchResults.length) { showToast(t("toast_no_copy")); return; }
  let text = searchResults.map((p, i) =>
    `${i+1}. ${p.title} (${p.year||"N/A"}) — ${truncateSentences(p.abstract,1)}`
  ).join("\n");
  navigator.clipboard.writeText(text).then(() =>
    showToast(t('toast_copied', searchResults.length))
  ).catch(() => showToast(t("toast_copy_fail")));
}

// ════════════════════════════════════════
//  GitHub Connection
// ════════════════════════════════════════

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
  if (!owner || !repo || !token) { showToast(t("toast_fill_github")); return; }
  localStorage.setItem(LS_OWNER, owner);
  localStorage.setItem(LS_REPO, repo);
  localStorage.setItem(LS_TOKEN, token);
  showToast(t("toast_config_loaded"));
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

function isConnected() { const gh = getGitHub(); return gh.owner && gh.repo && gh.token; }

function updateConnectionStatus() {
  const dot = document.querySelector(".dot");
  const text = document.querySelector(".status-text");
  if (isConnected()) { dot.classList.add("connected"); text.textContent = "已连接"; }
  else { dot.classList.remove("connected"); text.textContent = "未连接"; }
}

async function testConnection() {
  if (!isConnected()) { showToast("请先保存 GitHub 配置"); return; }
  const gh = getGitHub();
  try {
    const resp = await fetch(`https://api.github.com/repos/${gh.owner}/${gh.repo}`, { headers: { Authorization: `Bearer ${gh.token}` } });
    if (resp.ok) { showToast("✅ 连接成功！"); updateConnectionStatus(); }
    else { const d = await resp.json(); showToast(`❌ 连接失败: ${d.message || resp.status}`); }
  } catch (e) { showToast(`❌ 网络错误: ${e.message}`); }
}

function toggleTokenVisibility() {
  const input = document.getElementById("ghToken");
  input.type = input.type === "password" ? "text" : "password";
}

// ════════════════════════════════════════
//  Config Loading / Saving via GitHub API
// ════════════════════════════════════════

async function githubAPI(path, method = "GET", body = null) {
  const gh = getGitHub();
  const opts = { method, headers: { Authorization: `Bearer ${gh.token}`, Accept: "application/vnd.github.v3+json" } };
  if (body) { opts.headers["Content-Type"] = "application/json"; opts.body = JSON.stringify(body); }
  return fetch(`https://api.github.com/repos/${gh.owner}/${gh.repo}${path}`, opts);
}

async function loadConfigFromRepo() {
  if (!isConnected()) return;
  try {
    const resp = await githubAPI("/contents/config.json");
    if (!resp.ok) return;
    const data = await resp.json();
    const raw = atob(data.content.replace(/\n/g, ""));
    const bytes = new Uint8Array([...raw].map(c => c.charCodeAt(0)));
    config = JSON.parse(new TextDecoder("utf-8").decode(bytes));
    config._sha = data.sha;
    // Backward compat: if old "profiles" key exists, treat as push_profiles
    if (config.profiles && !config.push_profiles) {
      config.push_profiles = config.profiles;
      delete config.profiles;
    }
    if (!config.search_profiles) config.search_profiles = [];
    if (!config.push_profiles) config.push_profiles = [];
    renderPushProfiles();
    renderSearchProfiles();
    renderPushChecklist();
    renderSettings();
    showToast(t("toast_config_loaded"));
  } catch (e) { console.error("Failed to load config:", e); }
}

/**
 * Convert config schedule (local timezone) to a GitHub Actions UTC cron expression.
 * Returns e.g. "49 22 * * 1,2,3,4,5,6,0"
 */
function scheduleToCron(schedule, timezone) {
  const dayMap = { monday: 1, tuesday: 2, wednesday: 3, thursday: 4, friday: 5, saturday: 6, sunday: 0 };
  const localH = schedule.hour || 8;
  const localM = schedule.minute || 0;
  const days = schedule.days || [];
  if (!days.length) return null;

  // Use a known date to compute UTC offset for the given timezone.
  // Pick next occurrence to get correct DST offset.
  const probe = new Date();
  const localStr = probe.toLocaleString("en-US", { timeZone: timezone });
  const utcStr = probe.toLocaleString("en-US", { timeZone: "UTC" });
  const offsetMs = new Date(localStr) - new Date(utcStr);
  const offsetMin = Math.round(offsetMs / 60000); // positive = ahead of UTC

  // Convert local time to UTC
  let totalMin = localH * 60 + localM - offsetMin;
  let dayShift = 0;
  if (totalMin < 0) { totalMin += 1440; dayShift = -1; }
  else if (totalMin >= 1440) { totalMin -= 1440; dayShift = 1; }
  const utcH = Math.floor(totalMin / 60);
  const utcM = totalMin % 60;

  // Shift days if needed
  let cronDays = days.map(d => {
    let num = dayMap[d];
    if (num === undefined) return null;
    num = (num + dayShift + 7) % 7;
    return num;
  }).filter(d => d !== null);
  cronDays = [...new Set(cronDays)].sort((a, b) => a - b);

  return `${utcM} ${utcH} * * ${cronDays.join(",")}`;
}

/**
 * Sync the schedule from config.json to .github/workflows/push.yml via GitHub API.
 */
async function syncWorkflowSchedule(schedule, timezone) {
  if (!isConnected()) return;
  const cron = scheduleToCron(schedule, timezone);
  if (!cron) return;

  try {
    // Fetch current workflow file
    const resp = await githubAPI("/contents/.github/workflows/push.yml");
    if (!resp.ok) { console.warn("Could not fetch push.yml:", resp.status); return; }
    const data = await resp.json();
    const sha = data.sha;
    const raw = atob(data.content.replace(/\n/g, ""));
    const content = new TextDecoder("utf-8").decode(new Uint8Array([...raw].map(c => c.charCodeAt(0))));

    // Replace the cron line
    const updated = content.replace(
      /- cron:\s*'[^']*'.*/,
      `- cron: '${cron}'`
    );

    if (updated === content) { console.log("Cron line unchanged, skipping sync"); return; }

    // Commit updated workflow
    const bytes = new TextEncoder().encode(updated);
    const b64 = btoa(String.fromCharCode(...bytes));
    const putResp = await githubAPI("/contents/.github/workflows/push.yml", "PUT", {
      message: "🔄 sync push schedule from web UI",
      content: b64,
      sha,
    });
    if (putResp.ok) {
      showToast(t("toast_schedule_synced"));
    } else {
      const err = await putResp.json();
      console.error("Workflow sync failed:", err);
      showToast(t("toast_schedule_sync_fail"));
    }
  } catch (e) {
    console.error("Workflow sync error:", e);
    showToast(t("toast_schedule_sync_fail"));
  }
}

async function saveConfigToRepo() {
  if (!isConnected() || !config) return;
  const sha = config._sha;
  const copy = { ...config }; delete copy._sha;
  const jsonStr = JSON.stringify(copy, null, 2);
  const bytes = new TextEncoder().encode(jsonStr);
  const content = btoa(String.fromCharCode(...bytes));
  try {
    const resp = await githubAPI("/contents/config.json", "PUT", {
      message: "📝 update config from web UI", content, sha,
    });
    if (resp.ok) { config._sha = (await resp.json()).content.sha; showToast(t("toast_config_saved")); }
    else { const err = await resp.json(); showToast(`❌ 保存失败: ${err.message || resp.status}`); }
  } catch (e) { showToast(`❌ 保存错误: ${e.message}`); }
}

// ════════════════════════════════════════
//  Push Profiles
// ════════════════════════════════════════

function renderPushProfiles() {
  const container = document.getElementById("pushProfilesList");
  const profiles = (config && config.push_profiles) || [];
  if (!profiles.length) {
    container.innerHTML = `<div class="empty-state">${t("empty_push_profiles")}</div>`;
    return;
  }
  container.innerHTML = profiles.map((p, i) => {
    const dotClass = p.active ? "" : " inactive";
    return `
    <div class="profile-item">
      <div class="profile-info">
        <div class="profile-name"><span class="profile-active-dot${dotClass}"></span>${escHtml(p.name)}</div>
        <div class="profile-query">${escHtml(p.query)}</div>
        <div class="profile-meta">${escHtml(p.venue_filter||"any")} · ${p.count||"auto"} ${t("profile_meta_per")}</div>
      </div>
      <div class="profile-actions">
        <button class="btn btn-outline btn-sm" onclick="editPushProfile(${i})">${t("btn_edit")}</button>
        <button class="btn btn-danger btn-sm" onclick="deletePushProfile(${i})">${t("btn_delete")}</button>
      </div>
    </div>`;
  }).join("");
}

function renderPushChecklist() {
  const container = document.getElementById("pushProfileChecklist");
  const profiles = (config && config.push_profiles) || [];
  if (!profiles.length) {
    container.innerHTML = `<div class="empty-state">${t("empty_push_checklist")}</div>`;
    return;
  }
  container.innerHTML = profiles.map((p, i) => `
    <div class="push-profile-check">
      <label class="checkbox-label">
        <input type="checkbox" ${p.active ? "checked" : ""} onchange="togglePushActive(${i}, this.checked)"> ${escHtml(p.name)}
      </label>
      <div class="push-profile-count">
        <span>${t("checklist_each")}</span>
        <input type="number" min="1" max="20" value="${p.count||5}" onchange="updatePushCount(${i}, this.value)">
        <span>${t("checklist_unit")}</span>
      </div>
    </div>`).join("");
}

function togglePushActive(index, active) {
  if (!config || !config.push_profiles[index]) return;
  config.push_profiles[index].active = active;
  renderPushProfiles();
  saveConfigToRepo();
}

function updatePushCount(index, count) {
  if (!config || !config.push_profiles[index]) return;
  config.push_profiles[index].count = parseInt(count) || 5;
  renderPushProfiles();
  saveConfigToRepo();
}

function openPushProfileModal(index = -1) {
  editingPushIndex = index;
  const modal = document.getElementById("pushProfileModal");
  document.getElementById("pushModalTitle").textContent = index >= 0 ? t("modal_edit_push") : t("modal_add_push");
  if (index >= 0 && config && config.push_profiles[index]) {
    const p = config.push_profiles[index];
    document.getElementById("pushModalId").value = p.id;
    document.getElementById("pushModalName").value = p.name;
    document.getElementById("pushModalQuery").value = p.query;
    document.getElementById("pushModalVenue").value = p.venue_filter || "any";
    document.getElementById("pushModalCount").value = p.count || 5;
    document.getElementById("pushModalYearFrom").value = p.year_from || "";
  } else {
    document.getElementById("pushModalId").value = "";
    document.getElementById("pushModalName").value = "";
    document.getElementById("pushModalQuery").value = "";
    document.getElementById("pushModalVenue").value = "any";
    document.getElementById("pushModalCount").value = 5;
    document.getElementById("pushModalYearFrom").value = "";
  }
  modal.classList.remove("hidden");
}

function closePushProfileModal() {
  document.getElementById("pushProfileModal").classList.add("hidden");
  editingPushIndex = -1;
}

function savePushProfile() {
  const name = document.getElementById("pushModalName").value.trim();
  const query = document.getElementById("pushModalQuery").value.trim();
  if (!name || !query) { showToast(t("toast_fill_name_query")); return; }
  // Use existing ID when editing, auto-generate when creating
  const id = document.getElementById("pushModalId").value.trim() || nameToId(name);

  const pushYearVal = document.getElementById("pushModalYearFrom").value.trim();
  const profile = {
    id, name, query,
    sources: ["semantic_scholar", "openalex", "openreview"],
    venue_filter: document.getElementById("pushModalVenue").value,
    count: parseInt(document.getElementById("pushModalCount").value) || 5,
    year_from: pushYearVal ? parseInt(pushYearVal) : null,
    active: true,
  };

  if (!config) config = { push_profiles: [], search_profiles: [], venue_groups: {}, global: {} };
  if (!config.push_profiles) config.push_profiles = [];

  if (editingPushIndex >= 0) {
    config.push_profiles[editingPushIndex] = { ...config.push_profiles[editingPushIndex], ...profile };
  } else {
    if (config.push_profiles.some(p => p.id === id)) { showToast(t("toast_id_exists")); return; }
    config.push_profiles.push(profile);
  }
  closePushProfileModal();
  renderPushProfiles();
  renderPushChecklist();
  saveConfigToRepo();
}

function editPushProfile(i) { openPushProfileModal(i); }

function deletePushProfile(i) {
  if (!config || !config.push_profiles[i]) return;
  if (!confirm(t("confirm_delete", config.push_profiles[i].name))) return;
  config.push_profiles.splice(i, 1);
  renderPushProfiles();
  renderPushChecklist();
  saveConfigToRepo();
}

// ════════════════════════════════════════
//  Search Profiles
// ════════════════════════════════════════

function renderSearchProfiles() {
  const container = document.getElementById("searchProfilesList");
  const profiles = (config && config.search_profiles) || [];
  if (!profiles.length) {
    container.innerHTML = `<div class="empty-state">${t("empty_search_profiles")}</div>`;
    return;
  }
  container.innerHTML = profiles.map((p, i) => {
    const kwCount = (p.keyword_groups || []).length;
    const queryHint = p.query ? escHtml(p.query) : "";
    const kwHint = kwCount > 0 ? t("kw_groups_count", kwCount) : t("kw_groups_none");
    return `
    <div class="profile-item">
      <div class="profile-info">
        <div class="profile-name">${escHtml(p.name)}</div>
        ${queryHint ? `<div class="profile-query">${queryHint}</div>` : ""}
        <div class="profile-meta">${kwHint} · ${t("per_group_unit", p.max_per_group||25)}</div>
      </div>
      <div class="profile-actions">
        <button class="btn btn-primary btn-sm" onclick="loadSearchProfile(${i})">${t("btn_search_icon")}</button>
        <button class="btn btn-outline btn-sm" onclick="editSearchProfile(${i})">${t("btn_edit")}</button>
        <button class="btn btn-danger btn-sm" onclick="deleteSearchProfile(${i})">${t("btn_delete")}</button>
      </div>
    </div>`;
  }).join("");
}

function loadSearchProfile(index) {
  if (!config || !config.search_profiles[index]) return;
  const p = config.search_profiles[index];
  document.getElementById("searchQuery").value = p.query || p.name || "";
  const kwGroups = (p.keyword_groups || []);
  const kwArea = document.getElementById("searchKeywordGroups");
  kwArea.value = kwGroups.length > 0 ? kwGroups.map(g => g.join(", ")).join("\n") : "";
  document.getElementById("searchVenueFilter").value = p.venue_filter || "any";
  document.getElementById("searchMaxResults").value = p.max_per_group || 25;
  document.getElementById("searchYearFrom").value = p.year_from || "";
  showToast(t("toast_profile_loaded", p.name));
}

function openSearchProfileModal(index = -1) {
  editingSearchIndex = index;
  const modal = document.getElementById("searchProfileModal");
  document.getElementById("searchModalTitle").textContent = index >= 0 ? t("modal_edit_search") : t("modal_add_search");
  if (index >= 0 && config && config.search_profiles[index]) {
    const p = config.search_profiles[index];
    document.getElementById("searchModalId").value = p.id;
    document.getElementById("searchModalName").value = p.name;
    document.getElementById("searchModalQuery").value = p.query || "";
    document.getElementById("searchModalKeywords").value = (p.keyword_groups || []).map(g => g.join(", ")).join("\n");
    document.getElementById("searchModalVenue").value = p.venue_filter || "any";
    document.getElementById("searchModalMaxPerGroup").value = p.max_per_group || 25;
    document.getElementById("searchModalYearFrom").value = p.year_from || "";
  } else {
    document.getElementById("searchModalId").value = "";
    document.getElementById("searchModalName").value = "";
    document.getElementById("searchModalQuery").value = "";
    document.getElementById("searchModalKeywords").value = "";
    document.getElementById("searchModalVenue").value = "any";
    document.getElementById("searchModalMaxPerGroup").value = 25;
    document.getElementById("searchModalYearFrom").value = "";
  }
  modal.classList.remove("hidden");
}

function closeSearchProfileModal() {
  document.getElementById("searchProfileModal").classList.add("hidden");
  editingSearchIndex = -1;
}

function saveSearchProfile() {
  const name = document.getElementById("searchModalName").value.trim();
  const query = document.getElementById("searchModalQuery").value.trim();
  const kwText = document.getElementById("searchModalKeywords").value.trim();
  if (!name || (!query && !kwText)) { showToast(t("toast_fill_name_query_kw")); return; }
  const id = document.getElementById("searchModalId").value.trim() || nameToId(name);

  const keyword_groups = kwText ? kwText.split("\n")
    .map(line => line.trim()).filter(line => line)
    .map(line => line.split(",").map(kw => kw.trim()).filter(kw => kw)) : [];

  const yearVal = document.getElementById("searchModalYearFrom").value;
  const profile = {
    id, name, query, keyword_groups,
    sources: ["semantic_scholar", "openalex", "openreview"],
    venue_filter: document.getElementById("searchModalVenue").value,
    max_per_group: parseInt(document.getElementById("searchModalMaxPerGroup").value) || 25,
    year_from: yearVal ? parseInt(yearVal) : null,
  };

  if (!config) config = { push_profiles: [], search_profiles: [], venue_groups: {}, global: {} };
  if (!config.search_profiles) config.search_profiles = [];

  if (editingSearchIndex >= 0) {
    config.search_profiles[editingSearchIndex] = profile;
  } else {
    if (config.search_profiles.some(p => p.id === id)) { showToast(t("toast_id_exists")); return; }
    config.search_profiles.push(profile);
  }
  closeSearchProfileModal();
  renderSearchProfiles();
  saveConfigToRepo();
}

async function generateModalKeywords() {
  const query = document.getElementById("searchModalQuery").value.trim();
  const apiKey = localStorage.getItem(LS_OPENAI_KEY) || "";
  if (!query) { showToast(t("toast_fill_query")); return; }
  if (!apiKey) { showToast(t("toast_fill_apikey")); return; }

  showToast(t("toast_kw_modal_generating"));
  try {
    const resp = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Authorization": `Bearer ${apiKey}` },
      body: JSON.stringify({
        model: "gpt-5.4",
        messages: [
          { role: "system", content: GPT_KEYWORD_PROMPT },
          { role: "user", content: query },
        ],
        temperature: 0.3,
      }),
    });
    if (!resp.ok) { const err = await resp.json(); throw new Error(err.error?.message || resp.status); }
    const data = await resp.json();
    document.getElementById("searchModalKeywords").value = data.choices[0].message.content.trim();
    showToast(t("toast_kw_modal_done"));
  } catch (e) {
    showToast(`❌ 生成失败: ${e.message}`);
  }
}

function editSearchProfile(i) { openSearchProfileModal(i); }

function deleteSearchProfile(i) {
  if (!config || !config.search_profiles[i]) return;
  if (!confirm(t("confirm_delete", config.search_profiles[i].name))) return;
  config.search_profiles.splice(i, 1);
  renderSearchProfiles();
  saveConfigToRepo();
}

// ════════════════════════════════════════
//  Settings
// ════════════════════════════════════════

function renderSettings() {
  if (!config || !config.global) return;
  const g = config.global;
  document.getElementById("settEmail").value = g.email || "";
  document.getElementById("settTimezone").value = g.timezone || "America/Edmonton";
  document.getElementById("settSummaryLanguage").value = g.summary_language || "zh";
  if (g.schedule) {
    const days = g.schedule.days || [];
    ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"].forEach(d => {
      const el = document.getElementById("sched" + d);
      if (el) el.checked = days.includes(d.toLowerCase() === "thu" ? "thursday" :
        d.toLowerCase() + (d.length === 3 ? "day" : ""));
    });
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
  if (!config) config = { push_profiles: [], search_profiles: [], venue_groups: {}, global: {} };
  if (!config.global) config.global = {};
  config.global.email = document.getElementById("settEmail").value.trim();
  config.global.timezone = document.getElementById("settTimezone").value;
  config.global.summary_language = document.getElementById("settSummaryLanguage").value || "zh";
  const days = [];
  if (document.getElementById("schedMon").checked) days.push("monday");
  if (document.getElementById("schedTue").checked) days.push("tuesday");
  if (document.getElementById("schedWed").checked) days.push("wednesday");
  if (document.getElementById("schedThu").checked) days.push("thursday");
  if (document.getElementById("schedFri").checked) days.push("friday");
  if (document.getElementById("schedSat").checked) days.push("saturday");
  if (document.getElementById("schedSun").checked) days.push("sunday");
  const [hour, minute] = document.getElementById("schedTime").value.split(":").map(Number);
  config.global.schedule = { days, hour: hour || 8, minute: minute || 0 };
  saveConfigToRepo();
  // Sync schedule to GitHub Actions workflow cron
  const tz = config.global.timezone || "America/Edmonton";
  syncWorkflowSchedule(config.global.schedule, tz);
}

// ════════════════════════════════════════
//  Utilities
// ════════════════════════════════════════

function showToast(msg) {
  const toast = document.getElementById("toast");
  document.getElementById("toastMsg").textContent = msg;
  toast.classList.remove("hidden"); toast.classList.add("visible");
  setTimeout(() => { toast.classList.remove("visible"); setTimeout(() => toast.classList.add("hidden"), 300); }, 3000);
}

function escHtml(str) {
  const div = document.createElement("div"); div.textContent = str || ""; return div.innerHTML;
}

/** Generate a valid ID from any name (including Chinese). */
function nameToId(name) {
  // Replace Chinese chars with pinyin-like abbreviation using char codes
  let id = "";
  for (const ch of name.trim()) {
    if (/[a-zA-Z0-9]/.test(ch)) id += ch.toLowerCase();
    else if (ch === " " || ch === "-" || ch === "_") id += "_";
    else if (ch.charCodeAt(0) > 127) id += ch.charCodeAt(0).toString(36); // deterministic short hash per char
  }
  // Collapse multiple underscores, trim
  id = id.replace(/_+/g, "_").replace(/^_|_$/g, "");
  // Ensure not empty
  if (!id) id = "profile_" + Date.now().toString(36);
  // Ensure starts with letter
  if (/^[0-9]/.test(id)) id = "p_" + id;
  return id;
}
