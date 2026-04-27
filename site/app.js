let posts = [];
let fuse;

const els = {
  search: document.getElementById('search'),
  category: document.getElementById('categoryFilter'),
  tag: document.getElementById('tagFilter'),
  deadlineOnly: document.getElementById('deadlineOnly'),
  sortBy: document.getElementById('sortBy'),
  results: document.getElementById('results')
};

function render(items) {
  els.results.innerHTML = '';
  items.forEach(p => {
    const card = document.createElement('article');
    card.className = 'card';
    card.innerHTML = `
      <h3><a href="${p.archive_url}" target="_blank" rel="noopener">${p.subject}</a></h3>
      <div class="meta">${(p.date || '').slice(0,10)} · ${p.category}${p.deadline ? ` · deadline: ${p.deadline}` : ''}</div>
      <p>${p.snippet || ''}</p>
      <div class="tags">${(p.tags || []).map(t => `<span class="tag">${t}</span>`).join('')}</div>
    `;
    els.results.appendChild(card);
  });
}

function applyFilters() {
  const query = els.search.value.trim();
  const category = els.category.value;
  const tag = els.tag.value.trim().toLowerCase();
  const deadlineOnly = els.deadlineOnly.checked;

  let items = query ? fuse.search(query).map(x => x.item) : [...posts];

  items = items.filter(p => {
    if (category && p.category !== category) return false;
    if (tag && !(p.tags || []).map(t => t.toLowerCase()).includes(tag)) return false;
    if (deadlineOnly && !p.deadline) return false;
    return true;
  });

  if (els.sortBy.value === 'deadline') {
    items.sort((a, b) => (a.deadline || '9999').localeCompare(b.deadline || '9999'));
  } else {
    items.sort((a, b) => (b.date || '').localeCompare(a.date || ''));
  }

  render(items.slice(0, 300));
}

async function init() {
  const [postsResp, facetsResp] = await Promise.all([
    fetch('data/posts-latest.json'),
    fetch('data/facets.json')
  ]);
  posts = await postsResp.json();
  const facets = await facetsResp.json();

  Object.keys(facets.categories || {}).sort().forEach(c => {
    const opt = document.createElement('option');
    opt.value = c;
    opt.textContent = `${c} (${facets.categories[c]})`;
    els.category.appendChild(opt);
  });

  fuse = new Fuse(posts, { keys: ['subject', 'snippet', 'tags'], threshold: 0.3, ignoreLocation: true });

  Object.values(els).forEach(el => {
    if (el && (el.tagName === 'INPUT' || el.tagName === 'SELECT')) {
      el.addEventListener('input', applyFilters);
      el.addEventListener('change', applyFilters);
    }
  });

  applyFilters();
}

init().catch(err => {
  console.error(err);
  els.results.textContent = 'Failed to load data.';
});
