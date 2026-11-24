(async function () {
  const KEY = "contact-sheet-v1";
  const $ = (s, el = document) => el.querySelector(s);
  const board = $("#board"), status = $("#status");

  const base = await fetch("data.json", { cache: "no-cache" }).then((r) => r.json());
  const photos = Object.fromEntries(base.photos.map((p) => [p.id, p]));

  const store = {
    get() { try { return JSON.parse(localStorage.getItem(KEY)); } catch { return null; } },
    set(v) { try { localStorage.setItem(KEY, JSON.stringify(v)); return true; } catch { return false; } },
    clear() { try { localStorage.removeItem(KEY); } catch {} }
  };

  // Keep saved layouts valid if photos are added or removed later.
  function normalise(groups) {
    const known = new Set(Object.keys(photos)), seen = new Set();
    groups = groups.map((g) => ({ ...g, ids: g.ids.filter((id) => known.has(id) && !seen.has(id) && seen.add(id)) }));
    let un = groups.find((g) => g.id === "unplaced");
    if (!un) { un = { id: "unplaced", title: "Unplaced", note: "", ids: [] }; groups.push(un); }
    for (const id of known) if (!seen.has(id)) un.ids.push(id);
    return groups;
  }

  let state = normalise((store.get() || base).groups.map((g) => ({ ...g, ids: [...g.ids] })));
  const clone = (x) => JSON.parse(JSON.stringify(x));

  function save(msg) {
    const ok = store.set({ version: 1, groups: state });
    status.textContent = ok ? (msg || "Saved in this browser") : "Couldn't save here (private mode?). Use Export to keep your edits.";
  }

  function readDom() {
    state = [...board.querySelectorAll(".group")].map((el) => ({
      id: el.dataset.id,
      title: $(".g-title", el).value.trim() || "Untitled",
      note: $(".g-note", el).value,
      ids: [...el.querySelectorAll(".card")].map((c) => c.dataset.id)
    }));
  }

  function card(id, i) {
    const p = photos[id], el = document.createElement("div");
    el.className = "card"; el.dataset.id = id;
    el.style.aspectRatio = `${p.w} / ${p.h}`;
    el.innerHTML = `<img src="img/thumb/${id}.jpg" alt="Photo ${id}" loading="lazy" decoding="async"><span class="tag"><b>${i + 1}</b>${id}</span>`;
    return el;
  }

  function renumber() {
    board.querySelectorAll(".group").forEach((g) => {
      const cards = g.querySelectorAll(".card");
      cards.forEach((c, i) => ($(".tag b", c).textContent = g.dataset.id === "unplaced" ? "·" : i + 1));
      $(".g-count", g).textContent = `${cards.length} photo${cards.length === 1 ? "" : "s"}`;
    });
  }

  function render() {
    board.innerHTML = "";
    state.forEach((g) => {
      const el = document.createElement("section");
      el.className = "group" + (g.id === "unplaced" ? " unplaced" : "");
      el.dataset.id = g.id;
      el.innerHTML = `
        <div class="g-head">
          <input class="g-title" value="" aria-label="Series title">
          <span class="g-count"></span>
          ${g.id === "unplaced" ? "" : '<button class="g-del" title="Remove series (photos go to Unplaced)">Remove</button>'}
        </div>
        <textarea class="g-note" rows="2" placeholder="What connects these photos?"></textarea>
        <div class="sheet"></div>`;
      $(".g-title", el).value = g.title;
      $(".g-note", el).value = g.note || "";
      const sheet = $(".sheet", el);
      g.ids.forEach((id, i) => sheet.append(card(id, i)));
      board.append(el);

      new Sortable(sheet, {
        group: "photos", animation: 220, easing: "cubic-bezier(.2,.7,.2,1)",
        delay: 160, delayOnTouchOnly: true, touchStartThreshold: 6,
        ghostClass: "sortable-ghost", chosenClass: "sortable-chosen", dragClass: "sortable-drag",
        onEnd() { readDom(); renumber(); save(); }
      });

      $(".g-title", el).addEventListener("input", () => { readDom(); save(); });
      $(".g-note", el).addEventListener("input", () => { readDom(); save(); });
      const del = $(".g-del", el);
      if (del) del.addEventListener("click", () => {
        readDom();
        const g2 = state.find((x) => x.id === g.id);
        if (g2.ids.length && !confirm(`Remove "${g2.title}"? Its ${g2.ids.length} photos will move to Unplaced.`)) return;
        state = state.filter((x) => x.id !== g.id);
        state.find((x) => x.id === "unplaced").ids.unshift(...g2.ids);
        render(); save();
      });
    });
    renumber();
  }

  /* Toolbar */
  $("#add").addEventListener("click", () => {
    readDom();
    const idx = state.findIndex((g) => g.id === "unplaced");
    state.splice(idx, 0, { id: "s" + Date.now().toString(36), title: "New series", note: "", ids: [] });
    render(); save();
    const fresh = board.querySelectorAll(".group")[idx];
    fresh.scrollIntoView({ behavior: "smooth", block: "center" });
    $(".g-title", fresh).select();
  });

  $("#export").addEventListener("click", () => {
    readDom();
    const out = { version: 1, exported: new Date().toISOString(), groups: state };
    const blob = new Blob([JSON.stringify(out, null, 2)], { type: "application/json" });
    const a = Object.assign(document.createElement("a"), { href: URL.createObjectURL(blob), download: `contact-sheet-${new Date().toISOString().slice(0, 10)}.json` });
    document.body.append(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 2000);
    status.textContent = "Exported. Send this file to Claude to build the series pages.";
  });

  $("#import").addEventListener("change", async (e) => {
    const f = e.target.files[0]; if (!f) return;
    try {
      const data = JSON.parse(await f.text());
      if (!Array.isArray(data.groups)) throw new Error();
      state = normalise(data.groups); render(); save("Imported");
    } catch { status.textContent = "That file isn't a contact-sheet export."; }
    e.target.value = "";
  });

  $("#reset").addEventListener("click", () => {
    if (!confirm("Go back to the original suggested series? Your changes in this browser will be lost (export first if you want to keep them).")) return;
    store.clear(); state = normalise(clone(base.groups)); render(); save("Reset to suggestions");
  });

  const size = $("#size");
  const applySize = () => document.documentElement.style.setProperty("--h", size.value + "px");
  if (innerWidth < 640) size.value = 76;
  try { const s = localStorage.getItem(KEY + "-size"); if (s) size.value = s; } catch {}
  applySize();
  size.addEventListener("input", () => { applySize(); try { localStorage.setItem(KEY + "-size", size.value); } catch {} });

  /* Lightbox */
  const lb = $("#lightbox"), lbImg = $("img", lb), lbInfo = $(".lb-info", lb);
  let seq = [], pos = 0;
  function show(i) {
    pos = (i + seq.length) % seq.length;
    const id = seq[pos], p = photos[id];
    const g = state.find((x) => x.ids.includes(id));
    lbImg.src = `img/full/${id}.jpg`;
    lbInfo.innerHTML = `<b>${id}</b> · ${p.date} · ${p.file} · ${g ? g.title : ""} (${pos + 1}/${seq.length})`;
  }
  function open(id) {
    readDom();
    const g = state.find((x) => x.ids.includes(id));
    seq = g ? g.ids : [id]; show(seq.indexOf(id));
    lb.classList.add("open"); lb.setAttribute("aria-hidden", "false");
  }
  const close = () => { lb.classList.remove("open"); lb.setAttribute("aria-hidden", "true"); };
  board.addEventListener("click", (e) => { const c = e.target.closest(".card"); if (c) open(c.dataset.id); });
  $(".lb-close", lb).onclick = close;
  $(".lb-prev", lb).onclick = () => show(pos - 1);
  $(".lb-next", lb).onclick = () => show(pos + 1);
  lb.addEventListener("click", (e) => { if (e.target === lb) close(); });
  addEventListener("keydown", (e) => {
    if (!lb.classList.contains("open")) return;
    if (e.key === "Escape") close();
    if (e.key === "ArrowRight") show(pos + 1);
    if (e.key === "ArrowLeft") show(pos - 1);
  });
  let x0 = null;
  lb.addEventListener("touchstart", (e) => (x0 = e.touches[0].clientX), { passive: true });
  lb.addEventListener("touchend", (e) => {
    if (x0 === null) return; const dx = e.changedTouches[0].clientX - x0;
    if (Math.abs(dx) > 50) show(pos + (dx < 0 ? 1 : -1)); else if (Math.abs(dx) < 8 && e.target === lb) close();
    x0 = null;
  });

  render();
  status.textContent = store.get() ? "Your saved layout" : "Suggested series";
})();
