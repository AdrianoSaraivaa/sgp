(function () {
  "use strict";

  const MODELOS = ["PM700", "PM2100", "PM2200"];
  const MAX_ITENS = 10;

  const selModelo = document.getElementById("modeloSel");
  const tbody = document.getElementById("tbody");
  const btnAddItem = document.getElementById("btnAddItem");
  const btnAddItem2 = document.getElementById("btnAddItem2");
  const btnLimpar = document.getElementById("btnLimpar");
  const btnSalvar = document.getElementById("btnSalvar");
  const btnSalvar2 = document.getElementById("btnSalvar2");
  const btnAbrir = document.getElementById("btnAbrir");

  let itens = []; 
  // { descricao, tempo_alvo, min, max, bloqueante, exigeNota, ativo }

  function init() {
    selModelo.innerHTML = "";
    MODELOS.forEach(m => {
      const opt = document.createElement("option");
      opt.value = m; opt.textContent = m;
      selModelo.appendChild(opt);
    });

    btnAddItem.addEventListener("click", addItem);
    btnAddItem2.addEventListener("click", addItem);
    btnLimpar.addEventListener("click", limpar);
    btnSalvar.addEventListener("click", salvarNoSistema);
    btnSalvar2.addEventListener("click", salvarNoSistema);
    btnAbrir.addEventListener("click", abrirDoSistema);

    if (itens.length === 0) addItem();
  }

  function render() {
    tbody.innerHTML = "";
    itens.forEach((it, idx) => {
      tbody.appendChild(renderRow(it, idx));
    });
  }

  function renderRow(item, index) {
    const tr = document.createElement("tr");

    const tdOrdem = document.createElement("td");
    tdOrdem.className = "ordem";
    tdOrdem.textContent = index + 1;

    const tdDesc = document.createElement("td");
    const ta = document.createElement("textarea");
    ta.className = "desc";
    ta.placeholder = "Descreva o que checar";
    ta.value = item.descricao || "";
    ta.addEventListener("input", () => item.descricao = ta.value);
    tdDesc.appendChild(ta);

    function numCell(prop, placeholder) {
      const td = document.createElement("td");
      const inp = document.createElement("input");
      inp.className = "num";
      inp.type = "number"; inp.min = "0";
      inp.placeholder = placeholder;
      inp.value = item[prop] ?? "";
      inp.addEventListener("input", () => {
        const n = parseInt(inp.value, 10);
        item[prop] = Number.isFinite(n) && n >= 0 ? n : null;
      });
      td.appendChild(inp);
      return td;
    }

    function chkCell(prop) {
      const td = document.createElement("td");
      const chk = document.createElement("input");
      chk.type = "checkbox"; chk.className = "chk";
      chk.checked = !!item[prop];
      chk.addEventListener("change", () => item[prop] = chk.checked);
      td.appendChild(chk);
      return td;
    }

    const tdRem = document.createElement("td");
    const btn = document.createElement("button");
    btn.textContent = "×";
    btn.title = "Remover";
    btn.addEventListener("click", () => { itens.splice(index,1); render(); });
    tdRem.appendChild(btn);

    tr.appendChild(tdOrdem);
    tr.appendChild(tdDesc);
    tr.appendChild(numCell("tempo_alvo", "Alvo"));
    tr.appendChild(numCell("min", "Mín"));
    tr.appendChild(numCell("max", "Máx"));
    tr.appendChild(chkCell("bloqueante"));
    tr.appendChild(chkCell("exigeNota"));
    tr.appendChild(chkCell("ativo"));
    tr.appendChild(tdRem);

    return tr;
  }

  function addItem() {
    if (itens.length >= MAX_ITENS) {
      alert("Limite de 10 itens atingido.");
      return;
    }
    itens.push({ descricao:"", tempo_alvo:null, min:null, max:null, bloqueante:false, exigeNota:false, ativo:true });
    render();
  }

  function limpar() {
    if (!confirm("Limpar todos os itens?")) return;
    itens = [];
    addItem();
  }

  function montarPayload() {
    const modelo = selModelo.value || "";
    const errors = [];
    if (!modelo) errors.push("Selecione o modelo.");
    if (itens.length === 0) errors.push("Adicione pelo menos 1 item.");

    itens.forEach((it, idx) => {
      if (!it.descricao.trim()) errors.push(`Item ${idx+1}: descrição vazia.`);
      if (!Number.isFinite(it.tempo_alvo) || it.tempo_alvo <= 0) errors.push(`Item ${idx+1}: tempo alvo inválido.`);
    });

    if (errors.length) { alert(errors.join("\n")); return null; }

    return {
      modelo,
      itens: itens.map((it,i)=>({
        ordem: i+1,
        descricao: it.descricao.trim(),
        tempo_alvo_s: it.tempo_alvo,
        min_s: it.min,
        max_s: it.max,
        bloqueante: !!it.bloqueante,
        exige_nota_se_nao: !!it.exigeNota,
        habilitado: !!it.ativo
      }))
    };
  }

  async function salvarNoSistema() {
    const payload = montarPayload();
    if (!payload) return;
    try {
      const resp = await fetch("/api/gp/checklist/template", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify(payload)
      });
      const data = await resp.json();
      if (!resp.ok || !data.ok) throw new Error(data.error||"Falha ao salvar.");
      alert("Checklist salvo para o modelo " + payload.modelo);
    } catch(err){ alert("Erro: "+err.message); }
  }

  async function abrirDoSistema() {
    const modelo = selModelo.value || "";
    if (!modelo) { alert("Selecione o modelo"); return; }
    try {
      const resp = await fetch(`/api/gp/checklist/template/${encodeURIComponent(modelo)}`);
      const data = await resp.json();
      if (!resp.ok || !data.ok) throw new Error(data.error||"Falha ao carregar.");
      aplicarDoServidor(data.data);
    } catch(err){ alert("Erro: "+err.message); }
  }

  function aplicarDoServidor(template) {
    itens = (template.itens||[]).slice(0,MAX_ITENS).map(it=>({
      descricao: it.descricao||"",
      tempo_alvo: it.tempo_alvo_s||null,
      min: it.min_s||null,
      max: it.max_s||null,
      bloqueante: !!it.bloqueante,
      exigeNota: !!it.exige_nota_se_nao,
      ativo: !!it.habilitado
    }));
    if (template.modelo) selModelo.value = template.modelo;
    if (itens.length===0) addItem();
    render();
  }

  init();
})();
