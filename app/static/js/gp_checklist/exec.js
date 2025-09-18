(function(){
  "use strict";

  const HOLD_MS = 1000;
  const TOLERANCIA = 0.9;

  let checklist = null;
  let runningIndex = null;
  let itemsState = [];
  let holdTimer = null, holdStartAt = 0;
  let timers = [];

  const elLista = document.getElementById("lista");
  const elBtnCarregar = document.getElementById("btnCarregar");
  const elBtnFinalizar = document.getElementById("btnFinalizar");
  const elSerial = document.getElementById("serial");
  const elOperador = document.getElementById("operador");
  const elModeloInfo = document.getElementById("modeloInfo");

  const modalBg = document.getElementById("modalBg");
  const ncrSugestoes = document.getElementById("ncrSugestoes");
  const ncrCategoria = document.getElementById("ncrCategoria");
  const ncrDescricao = document.getElementById("ncrDescricao");
  const ncrFoto = document.getElementById("ncrFoto");
  const ncrSalvar = document.getElementById("ncrSalvar");
  const ncrCancelar = document.getElementById("ncrCancelar");
  let ncrForIndex = null;

  // Modal sucesso
  const doneBg = document.getElementById("doneBg");
  const doneOk = document.getElementById("doneOk");
  const doneMsg = document.getElementById("doneMsg");

  // ====== Eventos ======
  elSerial.addEventListener("change", tryLoadBySerial);
  elSerial.addEventListener("keydown", (e) => { if (e.key === "Enter") tryLoadBySerial(); });

  elBtnCarregar.addEventListener("click", () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "application/json";
    input.onchange = async () => {
      const f = input.files?.[0];
      if (!f) return;
      try {
        const json = JSON.parse(await f.text());
        carregarChecklist(json);
      } catch { alert("Arquivo inválido."); }
    };
    input.click();
  });

  elBtnFinalizar.addEventListener("click", finalizarChecklist_toServer);

  ncrCancelar.addEventListener("click", closeNcr);
  ncrSalvar.addEventListener("click", saveNcr);

  doneOk.addEventListener("click", () => {
    doneBg.style.display = "none";
    // opcional: limpar tela para próximo serial
    resetView();
  });

  // ====== Backend: carregar por serial ======
  async function tryLoadBySerial(){
    const serial = (elSerial.value || "").trim();
    if (!serial) return;
    window.__setExecStatus?.('warn', 'Buscando checklist...');
    try {
      const resp = await fetch(`/api/gp/checklist/by-serial/${encodeURIComponent(serial)}`);
      const data = await resp.json();
      if (!resp.ok || !data.ok) throw new Error(data.error || "Falha ao buscar checklist por serial.");
      elModeloInfo.value = data.modelo || "";
      carregarChecklist({
        modelo: data.modelo || (data.data && data.data.modelo) || "",
        items: (data.data && data.data.items) ? data.data.items.map(it => ({
          ordem: it.ordem ?? 0,
          descricao: it.descricao || "",
          tempo_seg: Number.isFinite(parseInt(it.tempo_seg,10)) ? parseInt(it.tempo_seg,10) : 0,
          ncr_tags: Array.isArray(it.ncr_tags) ? it.ncr_tags : []
        })) : []
      });
      window.__setExecStatus?.('ok', 'Checklist carregado.');
    } catch (err) {
      console.error(err);
      window.__setExecStatus?.('err', 'Erro ao carregar checklist.');
      alert("Não foi possível carregar o checklist para este serial: " + err.message);
    }
  }

  // ====== Renderização e timers ======
  function carregarChecklist(json){
    if (!json || !Array.isArray(json.items) || !json.items.length) {
      alert("Checklist vazio ou inválido.");
      return;
    }
    checklist = {
      modelo: json.modelo || "",
      items: json.items.map(i => ({
        ordem: i.ordem ?? 0,
        descricao: i.descricao || "",
        tempo_seg: Number.isFinite(parseInt(i.tempo_seg,10)) ? parseInt(i.tempo_seg,10) : 0,
        ncr_tags: Array.isArray(i.ncr_tags) ? i.ncr_tags : []
      }))
    };
    elModeloInfo.value = checklist.modelo || "";
    itemsState = checklist.items.map(() => ({
      status: "pendente",
      startedAt: null,
      finishedAt: null,
      elapsed: 0,
      ncrs: []
    }));
    timers = checklist.items.map(() => ({tickInterval:null, startedRealAt:null}));
    render();
    updateFinalizeBtn();
  }

  function render(){
    elLista.innerHTML = "";
    const sugeridas = checklist ? [...new Set(checklist.items.flatMap(i => i.ncr_tags || []))] : [];
    ncrSugestoes.innerHTML = "";
    sugeridas.forEach(s => { const o = document.createElement("option"); o.value = s; ncrSugestoes.appendChild(o); });
    if (!checklist) return;
    checklist.items.forEach((it, idx) => { elLista.appendChild(renderItem(it, idx)); });
  }

  function renderItem(it, idx){
    const st = itemsState[idx];
    const running = runningIndex === idx;
    const someoneRunning = runningIndex !== null && !running;

    const outer = document.createElement("div");
    outer.className = "item" + (someoneRunning ? " dim" : "");
    const h = document.createElement("h4");
    h.textContent = `${idx+1}. ${it.descricao}`;
    outer.appendChild(h);

    const meta = document.createElement("div");
    meta.className = "meta";
    meta.innerHTML = `
      <span><b>Tempo:</b> ${it.tempo_seg}s (libera aos ~${Math.ceil(it.tempo_seg*TOLERANCIA)}s)</span>
      <span><b>Status:</b> ${st.status === "ok" ? "<span class='status-ok'>OK</span>" :
                           st.status === "nok" ? "<span class='status-nok'>Não conforme</span>" :
                           "Pendente"}</span>
      <span><b>Gasto:</b> ${fmt(st.elapsed)}s</span>
    `;
    outer.appendChild(meta);

    const prog = document.createElement("div");
    prog.className = "progress";
    const bar = document.createElement("div");
    bar.className = "bar";
    bar.style.width = `${percentElapsed(st.elapsed, it.tempo_seg)}%`;
    prog.appendChild(bar);
    outer.appendChild(prog);

    if (it.ncr_tags && it.ncr_tags.length){
      const tags = document.createElement("div");
      tags.style.display = "flex"; tags.style.gap = "6px"; tags.style.flexWrap = "wrap";
      it.ncr_tags.forEach(t => {
        const span = document.createElement("span");
        span.className = "pill"; span.textContent = t;
        tags.appendChild(span);
      });
      outer.appendChild(tags);
    }

    const c = document.createElement("div");
    c.className = "controls";

    const btnHold = document.createElement("button");
    btnHold.textContent = running ? "Rodando..." : "Segure 1s p/ iniciar";
    btnHold.disabled = st.status !== "pendente" || someoneRunning;
    btnHold.addEventListener("mousedown", () => startHold(idx, btnHold));
    btnHold.addEventListener("touchstart", (e) => { e.preventDefault(); startHold(idx, btnHold); });
    ["mouseup","mouseleave","touchend","touchcancel"].forEach(ev => { btnHold.addEventListener(ev, cancelHold); });

    const btnOk = document.createElement("button");
    btnOk.textContent = "Concluir (OK)";
    btnOk.className = "primary";
    btnOk.disabled = !(running && canFinish(idx));
    btnOk.addEventListener("click", () => finish(idx, true));

    const btnNok = document.createElement("button");
    btnNok.textContent = "Não conforme";
    btnNok.className = "warn";
    btnNok.disabled = !(running && canFinish(idx));
    btnNok.addEventListener("click", () => openNcr(idx));

    const btnNcr = document.createElement("button");
    btnNcr.textContent = "Registrar ocorrência";
    btnNcr.disabled = running || st.status !== "pendente";
    btnNcr.addEventListener("click", () => openNcr(idx));

    c.appendChild(btnHold);
    c.appendChild(btnOk);
    c.appendChild(btnNok);
    c.appendChild(btnNcr);
    outer.appendChild(c);

    if (running) {
      const iv = setInterval(() => {
        const now = Date.now();
        st.elapsed = Math.floor((now - timers[idx].startedRealAt)/1000);
        bar.style.width = `${percentElapsed(st.elapsed, it.tempo_seg)}%`;
        btnOk.disabled = !canFinish(idx);
        btnNok.disabled = !canFinish(idx);
        meta.innerHTML = `
          <span><b>Tempo:</b> ${it.tempo_seg}s (libera aos ~${Math.ceil(it.tempo_seg*TOLERANCIA)}s)</span>
          <span><b>Status:</b> Rodando…</span>
          <span><b>Gasto:</b> ${fmt(st.elapsed)}s</span>
        `;
      }, 250);
      timers[idx].tickInterval = iv;
    }
    return outer;
  }

  // ===== timers / lógica =====
  function startHold(idx, btn){
    if (runningIndex !== null) return;
    holdStartAt = Date.now();
    holdTimer = setTimeout(() => { holdTimer = null; startRun(idx); btn.textContent = "Rodando..."; }, HOLD_MS);
  }
  function cancelHold(){ if (holdTimer) { clearTimeout(holdTimer); holdTimer = null; } }
  function startRun(idx){
    runningIndex = idx;
    itemsState[idx].startedAt = new Date().toISOString();
    timers[idx].startedRealAt = Date.now();
    rerenderAll();
  }
  function canFinish(idx){
    const it = checklist.items[idx];
    const st = itemsState[idx];
    return st.elapsed >= Math.ceil(it.tempo_seg * TOLERANCIA);
  }
  function finish(idx, ok){
    stopTimer(idx);
    const st = itemsState[idx];
    st.status = ok ? "ok" : "nok";
    st.finishedAt = new Date().toISOString();
    runningIndex = null;
    rerenderAll();
    updateFinalizeBtn();
  }
  function stopTimer(idx){
    if (timers[idx].tickInterval) {
      clearInterval(timers[idx].tickInterval);
      timers[idx].tickInterval = null;
    }
  }
  function rerenderAll(){
    timers.forEach((t,i)=>{ if (i!==runningIndex && t.tickInterval){ clearInterval(t.tickInterval); t.tickInterval=null; }});
    render();
  }

  // ===== Ocorrência / NCR =====
  function openNcr(idx){
    ncrForIndex = idx;
    ncrCategoria.value = "";
    ncrDescricao.value = "";
    ncrFoto.value = "";
    modalBg.style.display = "flex";
  }
  function closeNcr(){ modalBg.style.display = "none"; ncrForIndex = null; }
  function saveNcr(){
    if (ncrForIndex === null) return;
    const cat = (ncrCategoria.value || "").trim();
    const desc = (ncrDescricao.value || "").trim();
    const file = ncrFoto.files?.[0];

    const done = (fotoDataUrl) => {
      itemsState[ncrForIndex].ncrs.push({ categoria: cat || null, descricao: desc || null, fotoDataUrl: fotoDataUrl || null });
      closeNcr();
      render();
    };
    if (file) { const reader = new FileReader(); reader.onload = () => done(reader.result); reader.readAsDataURL(file); }
    else { done(null); }
  }

  // ===== Finalizar: enviar para o servidor (grava histórico) =====
  async function finalizarChecklist_toServer(){
    const serial = (elSerial.value || "").trim();
    if (!serial){ alert("Informe/escaneie o número de série."); return; }
    const pend = itemsState.findIndex(s => s.status === "pendente");
    if (pend >= 0){ alert("Ainda há itens pendentes."); return; }

    const operador = (elOperador.value || "").trim() || null;
    const payload = {
      serial,
      operador,
      modelo: checklist?.modelo || null,
      finished_at: new Date().toISOString(),
      items: checklist.items.map((it, i) => ({
        ordem: it.ordem ?? (i+1),
        descricao: it.descricao,
        tempo_estimado_seg: it.tempo_seg,
        status: itemsState[i].status,
        started_at: itemsState[i].startedAt,
        finished_at: itemsState[i].finishedAt,
        elapsed_seg: itemsState[i].elapsed,
        ncrs: itemsState[i].ncrs
      })),
      result: itemsState.every(s => s.status === "ok") ? "OK" : "NOK"
    };

    try {
      elBtnFinalizar.disabled = true;
      window.__setExecStatus?.('warn', 'Enviando resultados...');
      const resp = await fetch("/api/gp/checklist/exec", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload)
      });
      const data = await resp.json();
      if (!resp.ok || !data.ok) throw new Error(data.error || "Falha ao salvar execução.");

      // Sucesso: abre modal, marca status OK e bloqueia UI
      window.__setExecStatus?.('ok', 'Teste validado e armazenado.');
      doneMsg.textContent = "Teste validado e armazenado com sucesso.";
      doneBg.style.display = "flex";
      disableAll();
    } catch (err) {
      console.error(err);
      window.__setExecStatus?.('err', 'Erro ao salvar execução.');
      alert("Erro ao salvar a execução: " + err.message);
      elBtnFinalizar.disabled = false;
    }
  }

  function disableAll(){
    elSerial.disabled = true;
    elOperador.disabled = true;
    elBtnFinalizar.disabled = true;
    // Desabilita todos os botões de item
    elLista.querySelectorAll("button").forEach(b => b.disabled = true);
  }

  function resetView(){
    checklist = null;
    runningIndex = null;
    itemsState = [];
    timers = [];
    elLista.innerHTML = "";
    elModeloInfo.value = "";
    elSerial.value = "";
    elOperador.value = "";
    elSerial.disabled = false;
    elOperador.disabled = false;
    elBtnFinalizar.disabled = true;
    window.__setExecStatus?.('', 'Aguardando serial...');
    elSerial.focus();
  }

  function updateFinalizeBtn(){
    const ok = checklist && itemsState.length && itemsState.every(s => s.status !== "pendente");
    elBtnFinalizar.disabled = !ok;
  }

  // ===== helpers =====
  function percentElapsed(elapsed, total){ if (!total) return 0; return Math.min(100, Math.round((elapsed/total)*100)); }
  function fmt(n){ return Number.isFinite(n) ? n : 0; }
})();
