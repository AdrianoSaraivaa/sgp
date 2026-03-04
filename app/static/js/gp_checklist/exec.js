// ====================================================================
// [BLOCO] BLOCO_UTIL
// [NOME] IIFE (Immediately Invoked Function Expression)
// [RESPONSABILIDADE] Encapsular escopo do executor de checklist, gerenciar estado, UI, timers e integração com API
// ====================================================================
(function(){
  "use strict";

  // ====================================================================
  // [BLOCO] BLOCO_UTIL
  // [NOME] HOLD_MS
  // [RESPONSABILIDADE] Definir tempo de pressionar (hold) para iniciar item
  // ====================================================================
  const HOLD_MS = 1000;
  // ====================================================================
  // [FIM BLOCO] HOLD_MS
  // ====================================================================

  // ====================================================================
  // [BLOCO] BLOCO_UTIL
  // [NOME] TOLERANCIA
  // [RESPONSABILIDADE] Definir tolerância para liberar conclusão antes do tempo alvo total
  // ====================================================================
  const TOLERANCIA = 0.9;
  // ====================================================================
  // [FIM BLOCO] TOLERANCIA
  // ====================================================================

  // ====================================================================
  // [BLOCO] BLOCO_UTIL
  // [NOME] Estado (checklist/runningIndex/itemsState/hold/timers)
  // [RESPONSABILIDADE] Manter estado de execução do checklist e controle de timers/hold
  // ====================================================================
  let checklist = null;
  let runningIndex = null;
  let itemsState = [];
  let holdTimer = null, holdStartAt = 0;
  let timers = [];
  // ====================================================================
  // [FIM BLOCO] Estado (checklist/runningIndex/itemsState/hold/timers)
  // ====================================================================

  // ====================================================================
  // [BLOCO] BLOCO_UTIL
  // [NOME] Referências DOM (execução)
  // [RESPONSABILIDADE] Capturar elementos principais da UI do executor de checklist
  // ====================================================================
  const elLista = document.getElementById("lista");
  const elBtnCarregar = document.getElementById("btnCarregar");
  const elBtnFinalizar = document.getElementById("btnFinalizar");
  const elSerial = document.getElementById("serial");
  const elOperador = document.getElementById("operador");
  const elModeloInfo = document.getElementById("modeloInfo");
  // ====================================================================
  // [FIM BLOCO] Referências DOM (execução)
  // ====================================================================

  // ====================================================================
  // [BLOCO] BLOCO_UTIL
  // [NOME] Referências DOM (modal NCR)
  // [RESPONSABILIDADE] Capturar elementos do modal de ocorrência/não conformidade
  // ====================================================================
  const modalBg = document.getElementById("modalBg");
  const ncrSugestoes = document.getElementById("ncrSugestoes");
  const ncrCategoria = document.getElementById("ncrCategoria");
  const ncrDescricao = document.getElementById("ncrDescricao");
  const ncrFoto = document.getElementById("ncrFoto");
  const ncrSalvar = document.getElementById("ncrSalvar");
  const ncrCancelar = document.getElementById("ncrCancelar");
  let ncrForIndex = null;
  // ====================================================================
  // [FIM BLOCO] Referências DOM (modal NCR)
  // ====================================================================

  // ====================================================================
  // [BLOCO] BLOCO_UTIL
  // [NOME] Referências DOM (modal sucesso)
  // [RESPONSABILIDADE] Capturar elementos do modal de confirmação de finalização
  // ====================================================================
  // Modal sucesso
  const doneBg = document.getElementById("doneBg");
  const doneOk = document.getElementById("doneOk");
  const doneMsg = document.getElementById("doneMsg");
  // ====================================================================
  // [FIM BLOCO] Referências DOM (modal sucesso)
  // ====================================================================

  // ====================================================================
  // [BLOCO] BLOCO_UTIL
  // [NOME] Handlers de eventos (bootstrap)
  // [RESPONSABILIDADE] Registrar listeners para inputs, botões e fluxos de UI
  // ====================================================================
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
  // ====================================================================
  // [FIM BLOCO] Handlers de eventos (bootstrap)
  // ====================================================================

  // ====================================================================
  // [BLOCO] BLOCO_API
  // [NOME] tryLoadBySerial
  // [RESPONSABILIDADE] Buscar checklist por serial no backend e carregar no executor
  // ====================================================================
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
  // ====================================================================
  // [FIM BLOCO] tryLoadBySerial
  // ====================================================================

  // ====================================================================
  // [BLOCO] FUNÇÃO
  // [NOME] carregarChecklist
  // [RESPONSABILIDADE] Validar e normalizar JSON de checklist, preparar estado/timers e iniciar renderização
  // ====================================================================
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
  // ====================================================================
  // [FIM BLOCO] carregarChecklist
  // ====================================================================

  // ====================================================================
  // [BLOCO] FUNÇÃO
  // [NOME] render
  // [RESPONSABILIDADE] Renderizar lista de itens e preencher sugestões de NCR a partir do checklist
  // ====================================================================
  function render(){
    elLista.innerHTML = "";
    const sugeridas = checklist ? [...new Set(checklist.items.flatMap(i => i.ncr_tags || []))] : [];
    ncrSugestoes.innerHTML = "";
    sugeridas.forEach(s => { const o = document.createElement("option"); o.value = s; ncrSugestoes.appendChild(o); });
    if (!checklist) return;
    checklist.items.forEach((it, idx) => { elLista.appendChild(renderItem(it, idx)); });
  }
  // ====================================================================
  // [FIM BLOCO] render
  // ====================================================================

  // ====================================================================
  // [BLOCO] FUNÇÃO
  // [NOME] renderItem
  // [RESPONSABILIDADE] Construir UI de um item, associar controles e atualizar barra de progresso/timers quando rodando
  // ====================================================================
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
  // ====================================================================
  // [FIM BLOCO] renderItem
  // ====================================================================

  // ====================================================================
  // [BLOCO] FUNÇÃO
  // [NOME] startHold
  // [RESPONSABILIDADE] Iniciar contagem de hold para começar execução de um item
  // ====================================================================
  // ===== timers / lógica =====
  function startHold(idx, btn){
    if (runningIndex !== null) return;
    holdStartAt = Date.now();
    holdTimer = setTimeout(() => { holdTimer = null; startRun(idx); btn.textContent = "Rodando..."; }, HOLD_MS);
  }
  // ====================================================================
  // [FIM BLOCO] startHold
  // ====================================================================

  // ====================================================================
  // [BLOCO] FUNÇÃO
  // [NOME] cancelHold
  // [RESPONSABILIDADE] Cancelar o hold se o usuário soltar/cancelar antes do tempo mínimo
  // ====================================================================
  function cancelHold(){ if (holdTimer) { clearTimeout(holdTimer); holdTimer = null; } }
  // ====================================================================
  // [FIM BLOCO] cancelHold
  // ====================================================================

  // ====================================================================
  // [BLOCO] FUNÇÃO
  // [NOME] startRun
  // [RESPONSABILIDADE] Iniciar execução de um item, marcar timestamps e disparar re-renderização
  // ====================================================================
  function startRun(idx){
    runningIndex = idx;
    itemsState[idx].startedAt = new Date().toISOString();
    timers[idx].startedRealAt = Date.now();
    rerenderAll();
  }
  // ====================================================================
  // [FIM BLOCO] startRun
  // ====================================================================

  // ====================================================================
  // [BLOCO] FUNÇÃO
  // [NOME] canFinish
  // [RESPONSABILIDADE] Verificar se o item atual já atingiu o tempo mínimo para permitir conclusão
  // ====================================================================
  function canFinish(idx){
    const it = checklist.items[idx];
    const st = itemsState[idx];
    return st.elapsed >= Math.ceil(it.tempo_seg * TOLERANCIA);
  }
  // ====================================================================
  // [FIM BLOCO] canFinish
  // ====================================================================

  // ====================================================================
  // [BLOCO] FUNÇÃO
  // [NOME] finish
  // [RESPONSABILIDADE] Finalizar item (OK/NOK), parar timer, registrar timestamps e atualizar UI
  // ====================================================================
  function finish(idx, ok){
    stopTimer(idx);
    const st = itemsState[idx];
    st.status = ok ? "ok" : "nok";
    st.finishedAt = new Date().toISOString();
    runningIndex = null;
    rerenderAll();
    updateFinalizeBtn();
  }
  // ====================================================================
  // [FIM BLOCO] finish
  // ====================================================================

  // ====================================================================
  // [BLOCO] FUNÇÃO
  // [NOME] stopTimer
  // [RESPONSABILIDADE] Interromper intervalo de atualização do timer de um item
  // ====================================================================
  function stopTimer(idx){
    if (timers[idx].tickInterval) {
      clearInterval(timers[idx].tickInterval);
      timers[idx].tickInterval = null;
    }
  }
  // ====================================================================
  // [FIM BLOCO] stopTimer
  // ====================================================================

  // ====================================================================
  // [BLOCO] FUNÇÃO
  // [NOME] rerenderAll
  // [RESPONSABILIDADE] Re-renderizar lista e limpar intervals antigos não relacionados ao item rodando
  // ====================================================================
  function rerenderAll(){
    timers.forEach((t,i)=>{ if (i!==runningIndex && t.tickInterval){ clearInterval(t.tickInterval); t.tickInterval=null; }});
    render();
  }
  // ====================================================================
  // [FIM BLOCO] rerenderAll
  // ====================================================================

  // ====================================================================
  // [BLOCO] FUNÇÃO
  // [NOME] openNcr
  // [RESPONSABILIDADE] Abrir modal de NCR para um item específico e resetar campos
  // ====================================================================
  // ===== Ocorrência / NCR =====
  function openNcr(idx){
    ncrForIndex = idx;
    ncrCategoria.value = "";
    ncrDescricao.value = "";
    ncrFoto.value = "";
    modalBg.style.display = "flex";
  }
  // ====================================================================
  // [FIM BLOCO] openNcr
  // ====================================================================

  // ====================================================================
  // [BLOCO] FUNÇÃO
  // [NOME] closeNcr
  // [RESPONSABILIDADE] Fechar modal de NCR e limpar índice de referência
  // ====================================================================
  function closeNcr(){ modalBg.style.display = "none"; ncrForIndex = null; }
  // ====================================================================
  // [FIM BLOCO] closeNcr
  // ====================================================================

  // ====================================================================
  // [BLOCO] FUNÇÃO
  // [NOME] saveNcr
  // [RESPONSABILIDADE] Registrar ocorrência no estado do item, incluindo imagem opcional em data URL
  // ====================================================================
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
  // ====================================================================
  // [FIM BLOCO] saveNcr
  // ====================================================================

  // ====================================================================
  // [BLOCO] BLOCO_API
  // [NOME] finalizarChecklist_toServer
  // [RESPONSABILIDADE] Enviar execução concluída ao backend para persistência e sinalizar sucesso/erro na UI
  // ====================================================================
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
  // ====================================================================
  // [FIM BLOCO] finalizarChecklist_toServer
  // ====================================================================

  // ====================================================================
  // [BLOCO] FUNÇÃO
  // [NOME] disableAll
  // [RESPONSABILIDADE] Desabilitar inputs e botões para impedir alterações após finalização
  // ====================================================================
  function disableAll(){
    elSerial.disabled = true;
    elOperador.disabled = true;
    elBtnFinalizar.disabled = true;
    // Desabilita todos os botões de item
    elLista.querySelectorAll("button").forEach(b => b.disabled = true);
  }
  // ====================================================================
  // [FIM BLOCO] disableAll
  // ====================================================================

  // ====================================================================
  // [BLOCO] FUNÇÃO
  // [NOME] resetView
  // [RESPONSABILIDADE] Resetar estado e UI para iniciar novo checklist por serial
  // ====================================================================
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
  // ====================================================================
  // [FIM BLOCO] resetView
  // ====================================================================

  // ====================================================================
  // [BLOCO] FUNÇÃO
  // [NOME] updateFinalizeBtn
  // [RESPONSABILIDADE] Atualizar estado do botão finalizar conforme pendências do checklist
  // ====================================================================
  function updateFinalizeBtn(){
    const ok = checklist && itemsState.length && itemsState.every(s => s.status !== "pendente");
    elBtnFinalizar.disabled = !ok;
  }
  // ====================================================================
  // [FIM BLOCO] updateFinalizeBtn
  // ====================================================================

  // ====================================================================
  // [BLOCO] FUNÇÃO
  // [NOME] percentElapsed
  // [RESPONSABILIDADE] Calcular percentual de progresso com base no tempo decorrido e total
  // ====================================================================
  // ===== helpers =====
  function percentElapsed(elapsed, total){ if (!total) return 0; return Math.min(100, Math.round((elapsed/total)*100)); }
  // ====================================================================
  // [FIM BLOCO] percentElapsed
  // ====================================================================

  // ====================================================================
  // [BLOCO] FUNÇÃO
  // [NOME] fmt
  // [RESPONSABILIDADE] Normalizar valor numérico para exibição em UI
  // ====================================================================
  function fmt(n){ return Number.isFinite(n) ? n : 0; }
  // ====================================================================
  // [FIM BLOCO] fmt
  // ====================================================================

})();
// ====================================================================
// [FIM BLOCO] IIFE (Immediately Invoked Function Expression)
// ====================================================================

// ====================================================================
// MAPA DO ARQUIVO
// --------------------------------------------------------------------
// BLOCO_UTIL: IIFE (Immediately Invoked Function Expression)
// BLOCO_UTIL: HOLD_MS
// BLOCO_UTIL: TOLERANCIA
// BLOCO_UTIL: Estado (checklist/runningIndex/itemsState/hold/timers)
// BLOCO_UTIL: Referências DOM (execução)
// BLOCO_UTIL: Referências DOM (modal NCR)
// BLOCO_UTIL: Referências DOM (modal sucesso)
// BLOCO_UTIL: Handlers de eventos (bootstrap)
// BLOCO_API: tryLoadBySerial
// FUNÇÃO: carregarChecklist
// FUNÇÃO: render
// FUNÇÃO: renderItem
// FUNÇÃO: startHold
// FUNÇÃO: cancelHold
// FUNÇÃO: startRun
// FUNÇÃO: canFinish
// FUNÇÃO: finish
// FUNÇÃO: stopTimer
// FUNÇÃO: rerenderAll
// FUNÇÃO: openNcr
// FUNÇÃO: closeNcr
// FUNÇÃO: saveNcr
// BLOCO_API: finalizarChecklist_toServer
// FUNÇÃO: disableAll
// FUNÇÃO: resetView
// FUNÇÃO: updateFinalizeBtn
// FUNÇÃO: percentElapsed
// FUNÇÃO: fmt
// ====================================================================