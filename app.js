/* ========================================
   arXiv Paper Finder — App Logic
   ======================================== */

(function() {
  'use strict';

  const DATA_URL = 'data.json';
  const LS_THEME = 'ppf-theme';

  let papers = [];
  let filteredPapers = [];

  // ---- DOM refs ----
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  const grid = $('#papersGrid');
  const loadingEl = $('#loadingState');
  const emptyEl = $('#emptyState');
  const statsText = $('#statsText');
  const searchInput = $('#searchInput');
  const fieldFilter = $('#fieldFilter');
  const sortSelect = $('#sortSelect');
  const themeToggle = $('#themeToggle');
  const updateBadge = $('#updateBadge');
  const html = document.documentElement;

  // ---- Theme ----
  function initTheme() {
    const saved = localStorage.getItem(LS_THEME);
    if (saved) {
      html.setAttribute('data-theme', saved);
    }
    updateThemeToggle();
  }

  function toggleTheme() {
    const current = html.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', next);
    localStorage.setItem(LS_THEME, next);
    updateThemeToggle();
  }

  function updateThemeToggle() {
    const isDark = html.getAttribute('data-theme') === 'dark';
    themeToggle.textContent = isDark ? '☀️' : '🌙';
  }

  themeToggle.addEventListener('click', toggleTheme);

  // ---- Score helpers ----
  function scoreClass(score) {
    if (score == null) return '';
    if (score >= 8.5) return 'high';
    if (score >= 7.0) return 'mid';
    return 'low';
  }

  function formatDate(iso) {
    if (!iso) return '—';
    const d = new Date(iso);
    return d.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' });
  }

  function truncateAuthors(authors, max = 5) {
    if (!authors || authors.length === 0) return '—';
    const list = authors.slice(0, max);
    if (authors.length > max) list.push('et al.');
    return list.join(', ');
  }

  // ---- Render ----
  function render(papersList) {
    if (papersList.length === 0) {
      grid.innerHTML = '';
      emptyEl.style.display = 'block';
      statsText.textContent = '没有匹配的论文';
      return;
    }

    emptyEl.style.display = 'none';
    statsText.textContent = `共 ${papersList.length} 篇论文`;

    grid.innerHTML = papersList.map((p, i) => {
      const rank = i + 1;
      const rankClass = rank === 1 ? 'top-1' : rank === 2 ? 'top-2' : rank === 3 ? 'top-3' : '';

      const finalScore = p.final_score;
      const finalScoreHtml = finalScore != null
        ? `<span class="final-score-value ${scoreClass(finalScore)}">${finalScore.toFixed(1)}</span>`
        : '';

      const modelScoresHtml = p.model_scores
        ? Object.entries(p.model_scores).map(([name, score]) => {
            const label = name.length > 12 ? name.slice(0, 10) + '…' : name;
            return `<span class="model-score"><span class="label">${label}</span><span class="score-value ${scoreClass(score)}">${score != null ? score.toFixed(1) : '—'}</span></span>`;
          }).join('')
        : '';

      const categoriesHtml = p.categories
        ? p.categories.map(c => `<span class="category-tag">${c}</span>`).join('')
        : '';

      const keywordsHtml = p.keywords
        ? p.keywords.map(k => `<span class="keyword-tag">${k}</span>`).join('')
        : '';

      const field = p.field || '';
      const generalBadge = p.general ? '<span class="paper-general">通用领域</span>' : '';

      const reasonHtml = p.model_reasons
        ? Object.entries(p.model_reasons).map(([name, reason]) =>
            reason ? `<div><strong>${name}:</strong> ${reason}</div>` : ''
          ).join('')
        : '';

      return `
        <div class="paper-card">
          <div class="paper-header">
            <div class="paper-rank ${rankClass}">${rank}</div>
            <div class="paper-body">
              <div class="paper-title">
                <a href="https://arxiv.org/abs/${p.id}" target="_blank" rel="noopener">${p.title}</a>
              </div>
              <div class="paper-meta">
                <span class="paper-authors">${truncateAuthors(p.authors)}</span>
                <span class="meta-dot">·</span>
                <span>${formatDate(p.published)}</span>
                <span class="meta-dot">·</span>
                <span class="paper-categories">${categoriesHtml}</span>
              </div>
              <div class="paper-keywords">${keywordsHtml}</div>
              <div class="paper-footer">
                <div class="paper-field">
                  <strong>${field}</strong>${generalBadge}
                </div>
                <div class="paper-scores">
                  ${modelScoresHtml}
                  <div class="final-score">
                    ${finalScoreHtml}
                  </div>
                </div>
              </div>
              ${reasonHtml ? `<div class="paper-reason">${reasonHtml}</div>` : ''}
            </div>
          </div>
        </div>
      `;
    }).join('');
  }

  // ---- Filter & Sort ----
  function filterAndSort() {
    const query = searchInput.value.trim().toLowerCase();
    const field = fieldFilter.value;
    const sort = sortSelect.value;

    filteredPapers = papers.filter(p => {
      if (query) {
        const inTitle = p.title && p.title.toLowerCase().includes(query);
        const inAuthors = p.authors && p.authors.some(a => a.toLowerCase().includes(query));
        const inKeywords = p.keywords && p.keywords.some(k => k.toLowerCase().includes(query));
        if (!inTitle && !inAuthors && !inKeywords) return false;
      }
      if (field !== 'all') {
        if ((p.field || '') !== field) return false;
      }
      return true;
    });

    filteredPapers.sort((a, b) => {
      if (sort === 'score-desc') return (b.final_score || 0) - (a.final_score || 0);
      if (sort === 'date-desc') return new Date(b.published || 0) - new Date(a.published || 0);
      if (sort === 'date-asc') return new Date(a.published || 0) - new Date(b.published || 0);
      return 0;
    });

    render(filteredPapers);
  }

  // ---- Build field filter options ----
  function buildFieldFilter() {
    const fields = new Set();
    papers.forEach(p => { if (p.field) fields.add(p.field); });
    const sorted = Array.from(fields).sort();
    fieldFilter.innerHTML = '<option value="all">全部领域</option>' +
      sorted.map(f => `<option value="${f}">${f}</option>`).join('');
  }

  // ---- Load data ----
  async function loadData() {
    try {
      const resp = await fetch(DATA_URL + '?t=' + Date.now());
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();

      papers = data.papers || [];
      updateBadge.textContent = data.generated_at
        ? `更新于 ${formatDate(data.generated_at)} ${new Date(data.generated_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}`
        : '';

      if (papers.length > 0) {
        loadingEl.style.display = 'none';
        buildFieldFilter();
        filterAndSort();
      } else {
        loadingEl.innerHTML = '<p>暂无论文数据</p>';
      }
    } catch (err) {
      console.error('Failed to load papers data:', err);
      loadingEl.innerHTML = `
        <p>数据加载失败</p>
        <p style="font-size:0.8125rem;margin-top:0.5rem;color:var(--text-muted)">
          请确认已运行 <code>python main.py</code> 生成数据，或检查网络连接
        </p>
      `;
    }
  }

  // ---- Events ----
  searchInput.addEventListener('input', filterAndSort);
  fieldFilter.addEventListener('change', filterAndSort);
  sortSelect.addEventListener('change', filterAndSort);

  // ---- Init ----
  initTheme();
  loadData();
})();
