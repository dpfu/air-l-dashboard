let posts = [];
let fuse;
let pendingRender = null;
let threadIndex = { by_id: {}, threads: {} };
let monthStats = new Map();
let availableMonths = [];
let selectedMonths = new Set();
let selectedCategory = '';
let selectedDeadlineDate = '';

const els = {
  search: document.getElementById('search'),
  deadlineOnly: document.getElementById('deadlineOnly'),
  deadlineToggle: document.getElementById('deadlineToggle'),
  deadlinePanel: document.getElementById('deadlinePanel'),
  deadlineSummary: document.getElementById('deadlineSummary'),
  deadlineCalendar: document.getElementById('deadlineCalendar'),
  showThreads: document.getElementById('showThreads'),
  monthToggle: document.getElementById('monthToggle'),
  monthPanel: document.getElementById('monthPanel'),
  monthOptions: document.getElementById('monthOptions'),
  monthSummary: document.getElementById('monthSummary'),
  monthDefault: document.getElementById('monthDefault'),
  monthAll: document.getElementById('monthAll'),
  monthNone: document.getElementById('monthNone'),
  dashboard: document.getElementById('dashboard'),
  sortBy: document.getElementById('sortBy'),
  results: document.getElementById('results'),
  resultCount: document.getElementById('resultCount'),
  activeFilters: document.getElementById('activeFilters'),
  clearFilters: document.getElementById('clearFilters')
};

const CATEGORY_LABELS = {
  call_for_papers: 'CfP',
  publication: 'Publication',
  event: 'Events',
  job: 'JOBS',
  other: 'OTHER'
};

const CATEGORY_ORDER = ['call_for_papers', 'publication', 'event', 'job', 'other'];
const DASHBOARD_LABELS = {
  call_for_papers: 'CfP',
  publication: 'Pubs',
  event: 'Events',
  job: 'JOBS',
  other: 'Other'
};
const MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

function categoryLabel(category) {
  return CATEGORY_LABELS[category] || 'OTHER';
}

function formatDate(value) {
  return value ? value.slice(0, 10) : 'unknown';
}

function dayNumber(value) {
  return Number(value.slice(8, 10));
}

function postMonth(post) {
  const date = post.date || '';
  return /^\d{4}-\d{2}/.test(date) ? date.slice(0, 7) : 'unknown';
}

function monthLabel(month) {
  if (month === 'unknown') return 'unknown';
  const [year, rawMonth] = month.split('-').map(Number);
  const name = MONTH_NAMES[rawMonth - 1] || rawMonth;
  return `${name} ${year}`;
}

function compareMonthsAsc(a, b) {
  if (a === b) return 0;
  if (a === 'unknown') return 1;
  if (b === 'unknown') return -1;
  return a.localeCompare(b);
}

function compareMonthsDesc(a, b) {
  if (a === b) return 0;
  if (a === 'unknown') return 1;
  if (b === 'unknown') return -1;
  return b.localeCompare(a);
}

function previousMonthKey(month) {
  const [year, rawMonth] = month.split('-').map(Number);
  const date = new Date(Date.UTC(year, rawMonth - 2, 1));
  return `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, '0')}`;
}

function buildMonthStats() {
  monthStats = new Map();
  posts.forEach(post => {
    const month = postMonth(post);
    const category = CATEGORY_ORDER.includes(post.category) ? post.category : 'other';
    if (!monthStats.has(month)) {
      monthStats.set(month, { total: 0, categories: Object.fromEntries(CATEGORY_ORDER.map(key => [key, 0])) });
    }
    const stats = monthStats.get(month);
    stats.total += 1;
    stats.categories[category] += 1;
  });
  availableMonths = [...monthStats.keys()].sort(compareMonthsDesc);
}

function defaultMonthSelection() {
  const datedMonths = availableMonths.filter(month => month !== 'unknown').sort(compareMonthsAsc);
  if (datedMonths.length === 0) return new Set(availableMonths);
  const latest = datedMonths[datedMonths.length - 1];
  const previous = previousMonthKey(latest);
  const defaults = [latest, previous].filter(month => monthStats.has(month));
  return new Set(defaults.length ? defaults : [latest]);
}

function monthSelectionLabel(months = selectedMonths) {
  if (availableMonths.length === 0) return 'no months';
  if (months.size === 0) return 'no months';
  if (months.size === availableMonths.length) return 'all months';
  const selected = availableMonths.filter(month => months.has(month));
  if (selected.length <= 2) return selected.map(monthLabel).join(' + ');
  return `${selected.length} months`;
}

function syncMonthControls() {
  const selected = selectedMonths.size;
  const total = availableMonths.length;
  els.monthSummary.textContent = `${monthSelectionLabel()} · ${selected}/${total}`;
  els.monthToggle.textContent = `months ${selected}/${total}`;
  els.monthToggle.classList.toggle('active', !els.monthPanel.hidden);
  els.monthOptions.querySelectorAll('.month-choice').forEach(label => {
    const isActive = selectedMonths.has(label.dataset.month);
    label.classList.toggle('active', isActive);
    const input = label.querySelector('input');
    if (input) input.checked = isActive;
  });
}

function setSelectedMonths(months) {
  selectedMonths = new Set(months);
  syncMonthControls();
  applyFilters();
}

function setDeadlineDate(value) {
  const nextValue = selectedDeadlineDate === value ? '' : value;
  selectedDeadlineDate = nextValue;
  if (nextValue) {
    els.deadlineOnly.checked = false;
  }
  applyFilters();
}

function renderMonthOptions() {
  els.monthOptions.innerHTML = '';
  availableMonths.forEach(month => {
    const label = document.createElement('label');
    label.className = 'month-choice';
    label.dataset.month = month;

    const input = document.createElement('input');
    input.type = 'checkbox';
    input.value = month;
    input.checked = selectedMonths.has(month);

    const name = createTextEl('span', 'month-name', monthLabel(month));
    const count = createTextEl('span', 'month-count', String(monthStats.get(month)?.total || 0));

    label.append(input, name, count);
    input.addEventListener('change', () => {
      if (input.checked) selectedMonths.add(month);
      else selectedMonths.delete(month);
      syncMonthControls();
      applyFilters();
    });
    els.monthOptions.appendChild(label);
  });
  syncMonthControls();
}

function createTextEl(tag, className, text) {
  const el = document.createElement(tag);
  if (className) el.className = className;
  el.textContent = text;
  return el;
}

function normalizeThreadSubject(subject) {
  let value = (subject || '').toLowerCase();
  value = value.replace(/\[[^\]]*air-l[^\]]*\]/g, ' ');
  value = value.replace(/^\s*((re|fwd?|aw|sv)\s*:\s*)+/i, '');
  value = value.replace(/\s+/g, ' ').trim();
  return value || subject || '';
}

function groupThreads(items) {
  const groups = new Map();
  items.forEach(item => {
    const key = threadIndex.by_id[item.id]?.thread_id || normalizeThreadSubject(item.subject);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(item);
  });
  return [...groups.entries()].map(([key, threadItems]) => ({
    key,
    items: threadItems.sort((a, b) => {
      const aPosition = threadIndex.by_id[a.id]?.position;
      const bPosition = threadIndex.by_id[b.id]?.position;
      if (Number.isInteger(aPosition) && Number.isInteger(bPosition)) {
        return aPosition - bPosition;
      }
      return (b.date || '').localeCompare(a.date || '');
    }),
    representative: threadItems[0]
  }));
}

function renderRow(p, group, isThreadChild) {
  const row = document.createElement('li');
  row.className = isThreadChild ? 'row thread-child' : 'row';
  row.dataset.category = p.category || 'other';
  row.tabIndex = 0;
  row.setAttribute('role', 'link');
  row.setAttribute('aria-label', p.subject || 'Open archived message');

  const titleLine = document.createElement('div');
  titleLine.className = 'title-line';

  const category = createTextEl('span', 'category', categoryLabel(p.category));
  const title = document.createElement('a');
  title.className = 'title';
  title.href = p.archive_url;
  title.textContent = p.subject || 'Untitled';
  titleLine.append(category, title);

  const meta = document.createElement('div');
  meta.className = 'meta';
  meta.appendChild(createTextEl('span', '', formatDate(p.date)));

  if (!isThreadChild && group.items.length > 1) {
    meta.appendChild(createTextEl('span', 'thread-count', `${group.items.length} msgs`));
  }

  if (p.deadline) {
    meta.appendChild(createTextEl('span', 'deadline', `deadline ${p.deadline}`));
  }

  row.append(titleLine, meta);
  row.addEventListener('click', event => {
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    window.location.href = p.archive_url;
  });
  row.addEventListener('keydown', event => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      window.location.href = p.archive_url;
    }
  });
  return row;
}

function render(groups, showThreads) {
  els.results.innerHTML = '';

  if (groups.length === 0) {
    const row = document.createElement('li');
    row.className = 'row';
    row.appendChild(createTextEl('span', 'meta', 'No matches.'));
    els.results.appendChild(row);
    return;
  }

  groups.slice(0, 300).forEach(group => {
    els.results.appendChild(renderRow(group.representative, group, false));
    if (showThreads && group.items.length > 1) {
      group.items.slice(1).forEach(item => {
        els.results.appendChild(renderRow(item, group, true));
      });
    }
  });
}

function currentFilters() {
  return {
    query: els.search.value.trim(),
    category: selectedCategory,
    deadlineOnly: els.deadlineOnly.checked,
    deadlineDate: selectedDeadlineDate,
    months: new Set(selectedMonths),
    showThreads: els.showThreads.checked,
    sortBy: els.sortBy.value
  };
}

function filteredPosts(options = {}) {
  const includeCategory = options.includeCategory !== false;
  const includeMonths = options.includeMonths !== false;
  const includeDeadlineDate = options.includeDeadlineDate !== false;
  const sortItems = options.sort !== false;
  const filters = currentFilters();
  let items = filters.query ? fuse.search(filters.query).map(x => x.item) : [...posts];

  items = items.filter(p => {
    if (includeCategory && filters.category && p.category !== filters.category) return false;
    if (filters.deadlineOnly && !p.deadline) return false;
    if (includeDeadlineDate && filters.deadlineDate) {
      if (p.category !== 'call_for_papers' || p.deadline !== filters.deadlineDate) return false;
    }
    if (includeMonths && availableMonths.length && !filters.months.has(postMonth(p))) return false;
    return true;
  });

  if (!sortItems) return items;

  if (filters.sortBy === 'deadline') {
    items.sort((a, b) => {
      const byDeadline = (a.deadline || '9999').localeCompare(b.deadline || '9999');
      return byDeadline || (b.date || '').localeCompare(a.date || '');
    });
  } else {
    items.sort((a, b) => (b.date || '').localeCompare(a.date || ''));
  }

  return items;
}

function deadlineEntries(items) {
  return items
    .filter(post => post.category === 'call_for_papers' && post.deadline)
    .sort((a, b) => (a.deadline || '').localeCompare(b.deadline || '') || (b.date || '').localeCompare(a.date || ''));
}

function renderDeadlineCalendar(items) {
  const entries = deadlineEntries(items);
  els.deadlineCalendar.innerHTML = '';
  els.deadlineToggle.textContent = `calendar ${entries.length}`;
  els.deadlineToggle.classList.toggle('active', !els.deadlinePanel.hidden);

  if (selectedDeadlineDate) {
    const selectedCount = entries.filter(post => post.deadline === selectedDeadlineDate).length;
    els.deadlineSummary.textContent = `${selectedDeadlineDate} · ${selectedCount}`;
  } else {
    els.deadlineSummary.textContent = `${entries.length} dated CfPs`;
  }

  if (!entries.length) {
    els.deadlineCalendar.appendChild(createTextEl('div', 'meta', 'No CfP deadlines in the current scope.'));
    return;
  }

  const byMonth = new Map();
  entries.forEach(post => {
    const month = post.deadline.slice(0, 7);
    if (!byMonth.has(month)) byMonth.set(month, []);
    byMonth.get(month).push(post);
  });

  [...byMonth.keys()].sort(compareMonthsAsc).slice(0, 8).forEach(month => {
    const monthEntries = byMonth.get(month);
    const [year, rawMonth] = month.split('-').map(Number);
    const firstDay = new Date(Date.UTC(year, rawMonth - 1, 1));
    const daysInMonth = new Date(Date.UTC(year, rawMonth, 0)).getUTCDate();
    const offset = (firstDay.getUTCDay() + 6) % 7;
    const byDay = new Map();
    monthEntries.forEach(post => {
      const day = dayNumber(post.deadline);
      if (!byDay.has(day)) byDay.set(day, []);
      byDay.get(day).push(post);
    });

    const block = document.createElement('section');
    block.className = 'deadline-month';
    const heading = createTextEl('div', 'deadline-month-title', `${monthLabel(month)} · ${monthEntries.length}`);
    const grid = document.createElement('div');
    grid.className = 'deadline-grid';
    ['M', 'T', 'W', 'T', 'F', 'S', 'S'].forEach(label => {
      grid.appendChild(createTextEl('span', 'weekday', label));
    });

    for (let i = 0; i < offset; i += 1) {
      grid.appendChild(createTextEl('span', 'day blank', ''));
    }

    for (let day = 1; day <= daysInMonth; day += 1) {
      const dateKey = `${month}-${String(day).padStart(2, '0')}`;
      const dayEntries = byDay.get(day) || [];
      const cell = document.createElement(dayEntries.length ? 'button' : 'span');
      cell.className = dayEntries.length ? 'day has-deadline' : 'day';
      if (selectedDeadlineDate === dateKey) cell.classList.add('selected');
      cell.textContent = String(day);
      if (dayEntries.length) {
        cell.type = 'button';
        cell.title = dayEntries.map(post => post.subject).join('\n');
        cell.setAttribute('aria-label', `${dayEntries.length} CfP deadline${dayEntries.length === 1 ? '' : 's'} on ${dateKey}`);
        const count = createTextEl('span', 'day-count', String(dayEntries.length));
        cell.appendChild(count);
        cell.addEventListener('click', () => setDeadlineDate(dateKey));
      }
      grid.appendChild(cell);
    }

    block.append(heading, grid);
    els.deadlineCalendar.appendChild(block);
  });
}

function renderDashboard(items) {
  els.dashboard.innerHTML = '';
  const months = [...availableMonths].sort(compareMonthsAsc);
  if (months.length === 0) return;

  const counts = Object.fromEntries(CATEGORY_ORDER.map(category => [category, new Map()]));
  items.forEach(post => {
    const category = CATEGORY_ORDER.includes(post.category) ? post.category : 'other';
    const month = postMonth(post);
    counts[category].set(month, (counts[category].get(month) || 0) + 1);
  });

  CATEGORY_ORDER.forEach(category => {
    const metric = document.createElement('button');
    metric.type = 'button';
    metric.className = 'metric';
    metric.dataset.category = category;
    metric.title = `Filter ${categoryLabel(category)}`;
    metric.classList.toggle('active', selectedCategory === category);

    const selectedTotal = months.reduce((total, month) => {
      if (!selectedMonths.has(month)) return total;
      return total + (counts[category].get(month) || 0);
    }, 0);
    const seriesMax = Math.max(1, ...months.map(month => counts[category].get(month) || 0));

    const label = createTextEl('span', 'metric-label', DASHBOARD_LABELS[category] || categoryLabel(category));
    const count = createTextEl('span', 'metric-count', String(selectedTotal));
    const spark = document.createElement('span');
    spark.className = 'spark';

    months.forEach(month => {
      const value = counts[category].get(month) || 0;
      const bar = document.createElement('span');
      bar.className = selectedMonths.has(month) ? 'active' : '';
      bar.style.height = `${Math.max(2, Math.round((value / seriesMax) * 16))}px`;
      bar.title = `${monthLabel(month)}: ${value}`;
      spark.appendChild(bar);
    });

    metric.append(label, count, spark);
    metric.addEventListener('click', () => {
      selectedCategory = selectedCategory === category ? '' : category;
      applyFilters();
    });
    els.dashboard.appendChild(metric);
  });
}

function updateFilterChrome(threadCount, messageCount) {
  const filters = currentFilters();
  const active = [];
  if (filters.query) active.push(`q:${filters.query}`);
  if (filters.category) active.push(categoryLabel(filters.category));
  if (filters.deadlineOnly) active.push('deadline');
  if (filters.deadlineDate) active.push(`CfP due ${filters.deadlineDate}`);
  if (availableMonths.length) active.push(monthSelectionLabel(filters.months));
  if (filters.showThreads) active.push('threads');
  if (filters.sortBy !== 'newest') active.push(filters.sortBy);

  els.resultCount.textContent = `${threadCount} thread${threadCount === 1 ? '' : 's'} · ${messageCount} msg${messageCount === 1 ? '' : 's'}`;
  els.activeFilters.textContent = active.join(' · ');
}

function applyFilters() {
  if (pendingRender) cancelAnimationFrame(pendingRender);
  pendingRender = requestAnimationFrame(() => {
    renderDashboard(filteredPosts({ includeCategory: false, includeMonths: false, includeDeadlineDate: false, sort: false }));
    renderDeadlineCalendar(filteredPosts({ includeCategory: false, includeDeadlineDate: false, sort: false }));
    const items = filteredPosts();
    const groups = groupThreads(items);
    updateFilterChrome(groups.length, items.length);
    render(groups, currentFilters().showThreads);
  });
}

function clearFilters() {
  els.search.value = '';
  selectedCategory = '';
  selectedDeadlineDate = '';
  els.deadlineOnly.checked = false;
  els.showThreads.checked = false;
  els.sortBy.value = 'newest';
  selectedMonths = defaultMonthSelection();
  syncMonthControls();
  applyFilters();
}

async function init() {
  const [postsResp, threadResp] = await Promise.all([
    fetch('data/search-index.json'),
    fetch('data/thread-index.json').catch(() => null)
  ]);
  posts = await postsResp.json();
  if (threadResp?.ok) {
    threadIndex = await threadResp.json();
  }

  buildMonthStats();
  selectedMonths = defaultMonthSelection();
  renderMonthOptions();

  fuse = new Fuse(posts, { keys: ['subject', 'snippet', 'tags', 'category'], threshold: 0.28, ignoreLocation: true });

  [els.search, els.deadlineOnly, els.showThreads, els.sortBy].forEach(el => {
    el.addEventListener('input', applyFilters);
    el.addEventListener('change', applyFilters);
  });

  els.deadlineToggle.addEventListener('click', () => {
    const expanded = els.deadlinePanel.hidden;
    els.deadlinePanel.hidden = !expanded;
    els.deadlineToggle.setAttribute('aria-expanded', String(expanded));
    applyFilters();
  });

  els.monthToggle.addEventListener('click', () => {
    const expanded = els.monthPanel.hidden;
    els.monthPanel.hidden = !expanded;
    els.monthToggle.setAttribute('aria-expanded', String(expanded));
    syncMonthControls();
  });
  els.monthDefault.addEventListener('click', () => setSelectedMonths(defaultMonthSelection()));
  els.monthAll.addEventListener('click', () => setSelectedMonths(availableMonths));
  els.monthNone.addEventListener('click', () => setSelectedMonths([]));

  els.clearFilters.addEventListener('click', clearFilters);

  document.addEventListener('keydown', event => {
    if (event.key === '/' && document.activeElement !== els.search) {
      event.preventDefault();
      els.search.focus();
    }
    if (event.key === 'Escape') {
      clearFilters();
      els.search.blur();
    }
  });

  applyFilters();
}

init().catch(err => {
  console.error(err);
  els.results.textContent = 'Failed to load data.';
});
