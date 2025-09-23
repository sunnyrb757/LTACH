(function(){
  const SNAP = '/data/external_facilities.enriched.carf.manual.json';
  async function loadData(){
    try{
      const r = await fetch(SNAP + '?_=' + Date.now());
      if(!r.ok) throw new Error('Failed to fetch snapshot: '+r.status);
      return await r.json();
    }catch(e){
      console.error(e);
      document.getElementById('summary').innerText = 'Error loading snapshot: '+e;
      return [];
    }
  }

  function isLTACH(item){
    const t = (item.type||'').toLowerCase();
    const tags = (item.tags||[]).map(s=>s.toLowerCase());
    return t.indexOf('ltach')>=0 || tags.includes('ltach') || (item.programs||[]).map(s=>s.toLowerCase()).includes('tbi')===false && (t.indexOf('inpatient')>=0 && (item.name||'').toLowerCase().includes('ltach'));
  }
  function isTBI(item){
    const programs = (item.programs||[]).map(s=>s.toLowerCase());
    const name = (item.name||'').toLowerCase();
    return programs.includes('tbi') || name.includes('tbi') || name.includes('traumatic brain') || name.includes('brain injury');
  }

  function stateFor(item){
    // Prefer explicit structured fields
    if(item && item.state) return item.state;
    if(item && item.address && item.address.state) return item.address.state;
    if(item && item.location && item.location.state) return item.location.state;
    // Heuristic: try to derive from common id formats like 'city-state-...' or 'slug-with-state'
    // Example id patterns: 'kessler-institute-for-rehabilitation-nj' or 'medstar-national-rehab-md'
    if(item && item.id && typeof item.id === 'string'){
      const toks = item.id.split(/[-_]/).map(t=>t.trim()).filter(Boolean);
      // look for a 2-letter state code token
      for(const t of toks){ if(/^[A-Za-z]{2}$/.test(t)){ return t.toUpperCase(); } }
      // last token may be a state name or abbreviation
      const last = toks[toks.length-1]; if(last && last.length<=3) return last.toUpperCase();
    }
    // Heuristic: try to find a US state in the 'location' free-text (e.g., 'West Orange, NJ')
    if(item && item.location && typeof item.location === 'string'){
      const m = item.location.match(/,\s*([A-Za-z]{2})$/);
      if(m && m[1]) return m[1].toUpperCase();
      // match full state names (e.g., 'New Jersey') and map to abbreviation
      const stateMap = {
        'alabama':'AL','alaska':'AK','arizona':'AZ','arkansas':'AR','california':'CA','colorado':'CO','connecticut':'CT','delaware':'DE','florida':'FL','georgia':'GA','hawaii':'HI','idaho':'ID','illinois':'IL','indiana':'IN','iowa':'IA','kansas':'KS','kentucky':'KY','louisiana':'LA','maine':'ME','maryland':'MD','massachusetts':'MA','michigan':'MI','minnesota':'MN','mississippi':'MS','missouri':'MO','montana':'MT','nebraska':'NE','nevada':'NV','new hampshire':'NH','new jersey':'NJ','new mexico':'NM','new york':'NY','north carolina':'NC','north dakota':'ND','ohio':'OH','oklahoma':'OK','oregon':'OR','pennsylvania':'PA','rhode island':'RI','south carolina':'SC','south dakota':'SD','tennessee':'TN','texas':'TX','utah':'UT','vermont':'VT','virginia':'VA','washington':'WA','west virginia':'WV','wisconsin':'WI','wyoming':'WY','district of columbia':'DC'
      };
      const locLower = item.location.toLowerCase();
      for(const name in stateMap){ if(locLower.indexOf(name) >= 0) return stateMap[name]; }
    }
    return 'Unknown';
  }

  function aggregate(data, opts){
    const groups = {};
    for(const item of data){
      if(opts.requireLTACH && !isLTACH(item)) continue;
      if(opts.requireTBI && !isTBI(item)) continue;
      const st = (stateFor(item)||'Unknown').toUpperCase();
      const g = groups[st] = groups[st]||{state:st,count:0,carf_count:0,therapy_hours:0,facilities:[]};
      g.count += 1;
      if(item.carf) g.carf_count += 1;
      g.therapy_hours += Number(item.therapy_hours||0);
      g.facilities.push(item);
    }
    return Object.values(groups);
  }

  function renderTable(groups, metric){
    groups.sort((a,b)=>b[metric]-a[metric]);
    const top = groups.slice(0,50);
    const el = document.getElementById('leaderboard');
    el.innerHTML = '';
    const tbl = document.createElement('table');
    const h = document.createElement('thead');
    h.innerHTML = '<tr><th>Rank</th><th>State</th><th>Count</th><th>CARF Count</th><th>Therapy Hours</th></tr>';
    tbl.appendChild(h);
    const b = document.createElement('tbody');
    top.forEach((g,i)=>{
      const tr = document.createElement('tr');
      tr.innerHTML = `<td>${i+1}</td><td>${g.state}</td><td>${g.count}</td><td>${g.carf_count}</td><td>${g.therapy_hours.toFixed(1)}</td>`;
      b.appendChild(tr);
    });
    tbl.appendChild(b);
    el.appendChild(tbl);
  }

  async function refresh(){
    document.getElementById('summary').innerText = 'Loading snapshot...';
    const data = await loadData();
    if(!data || data.length===0){
      document.getElementById('summary').innerText = 'No data loaded.';
      return;
    }
    document.getElementById('summary').innerText = `Loaded ${data.length} facilities.`;
    const requireLTACH = document.getElementById('filter-ltach').checked;
    const requireTBI = document.getElementById('filter-tbi').checked;
    const metric = document.getElementById('metric').value;
    const groups = aggregate(data, {requireLTACH, requireTBI});
    renderTable(groups, metric);
  }

  document.getElementById('refresh').addEventListener('click', refresh);
  window.addEventListener('load', refresh);
})();