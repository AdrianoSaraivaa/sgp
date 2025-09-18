(function () {
  "use strict";

  // ======= Config simples (pode vir do backend depois) =======
  const MODELOS = ["PM700", "PM2100", "PM2200"]; // ajuste se precisar
  const SUGESTOES_NC = [
    "AJUSTE", "REBARBA", "DEFEITO NA ROSETA", "DEFEITO DE USINAGEM",
    "PINTURA", "FALTA DE PEÇA", "MONTAGEM INCORRETA"
  ];
  const MAX_ITENS = 10;

  // ======= DOM =======
  const selModelo = document.getElementById("modeloSel");
  const tbody = document.getElementById("tbody");
  const btnAddItem = document.getElementById("btnAddItem");
  const btnAddItem2 = document.getElementById("btnAddItem2");
  const btnLimpar = document.getElementById("btnLimpar");
  const btnSalvar = document.getElementById("btnSalvar");
  const btnSalvar2 = document.getElementById("btnSalvar2");
  const btnAbrir = document.getElementById("btnAbrir");

  // ======= Estado =======
  let itens = []; // { descricao: string, tempo_seg: number|null, ncr_tags: string[] }

  // ======= Inicialização =======
  function init() {
    // Preenche select de modelos
    selModelo.innerHTML = "";
    MODELOS.forEach(m => {
      const opt = document.createElement("option");
      opt.value = m; opt.textContent = m;
      selModelo.appendChild(opt);
    });













    (function() {
  const params = new URLSearchParams(window.location.search);
  const modeloURL = params.get('modelo');
  const sel = document.getElementById('modeloSel');
  if (modeloURL && sel) {
    sel.value = modeloURL;
  }
})();










document.getElementById('btnSalvar').addEventListener('click', () => {
  const data = serialize();
  fetch("/producao/gp/setup/save", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify(data)
  })
  .then(r => r.ok ? r.json() : Promise.reject())
  .then(() => { msg.textContent = `Roteiro do modelo ${state.modelo} salvo com sucesso.`; })
  .catch(() => { msg.textContent = "Falha ao salvar o roteiro."; });
});









    // Eventos
    btnAddItem.addEventListener("click", addItem);
    btnAddItem2.addEventListener("click", addItem);
    btnLimpar.addEventListener("click", limpar);
    btnSalvar.addEventListener("click", salvarNoSistema);
    btnSalvar2.addEventListener("click", salvarNoSistema);
    btnAbrir.addEventListener("click", abrirDoSistema);

    // Um item inicial para guiar o uso
    if (itens.length === 0) addItem();
  }

  // ======= UI helpers =======
  function render() {
    tbody.innerHTML = "";
    itens.forEach((it, idx) => {
      tbody.appendChild(renderRow(it, idx));
    });
  }

  function renderRow(item, index) {
    const tr = document.createElement("tr");

    // Ordem (auto)
    const tdOrdem = document.createElement("td");
    tdOrdem.className = "ordem";
    tdOrdem.textContent = index + 1;

    // Descrição (textarea auto-ajuste)
    const tdDesc = document.createElement("td");
    const ta = document.createElement("textarea");
    ta.className = "desc";
    ta.placeholder = "Descreva o que checar (ex.: Verificar aperto dos parafusos da tampa)";
    ta.value = item.descricao || "";
    ta.addEventListener("input", () => {
      item.descricao = ta.value;
      autoGrow(ta);
    });
    setTimeout(() => autoGrow(ta), 0);
    tdDesc.appendChild(ta);

    // Tempo estimado
    const tdTempo = document.createElement("td");
    const inpTempo = document.createElement("input");
    inpTempo.className = "tempo";
    inpTempo.type = "number";
    inpTempo.min = "1";
    inpTempo.placeholder = "ex.: 30";
    inpTempo.value = item.tempo_seg ?? "";
    inpTempo.addEventListener("input", () => {
      const n = parseInt(inpTempo.value, 10);
      item.tempo_seg = Number.isFinite(n) && n > 0 ? n : null;
    });
    tdTempo.appendChild(inpTempo);

    // NCR tags por item
    const tdTags = document.createElement("td");
    const tagsWrap = document.createElement("div");
    tagsWrap.className = "tags";
    const inputWrap = document.createElement("div");
    inputWrap.className = "tag-input";

    const inpTag = document.createElement("input");
    inpTag.type = "text";
    inpTag.placeholder = "Adicionar não conformidade (ENTER)";

    // Sugestões simples (autocomplete leve)
    const datalistId = `dl_${index}`;
    const dl = document.createElement("datalist");
    dl.id = datalistId;
    SUGESTOES_NC.forEach(s => {
      const o = document.createElement("option");
      o.value = s;
      dl.appendChild(o);
    });
    inpTag.setAttribute("list", datalistId);

    const btnAddTag = document.createElement("button");
    btnAddTag.textContent = "Adicionar";
    btnAddTag.type = "button";

    function addTagFromInput() {
      const v = (inpTag.value || "").trim();
      if (!v) return;
      if (!item.ncr_tags.includes(v)) {
        item.ncr_tags.push(v);
        renderTags();
      }
      inpTag.value = "";
      inpTag.focus();
    }

    inpTag.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        addTagFromInput();
      }
    });
    btnAddTag.addEventListener("click", addTagFromInput);

    function renderTags() {
      tagsWrap.innerHTML = "";
      item.ncr_tags.forEach((t, i) => {
        const tag = document.createElement("span");
        tag.className = "tag";
        tag.textContent = t + " ";
        const x = document.createElement("button");
        x.textContent = "×";
        x.title = "Remover";
        x.addEventListener("click", () => {
          item.ncr_tags.splice(i, 1);
          renderTags();
        });
        tag.appendChild(x);
        tagsWrap.appendChild(tag);
      });
    }
    renderTags();

    inputWrap.appendChild(inpTag);
    inputWrap.appendChild(btnAddTag);
    tdTags.appendChild(tagsWrap);
    tdTags.appendChild(inputWrap);
    tdTags.appendChild(dl);

    // Remover linha
    const tdAcoes = document.createElement("td");
    tdAcoes.className = "acoes";
    const btnRem = document.createElement("button");
    btnRem.textContent = "×";
    btnRem.title = "Remover item";
    btnRem.addEventListener("click", () => {
      itens.splice(index, 1);
      render();
    });
    tdAcoes.appendChild(btnRem);

    tr.appendChild(tdOrdem);
    tr.appendChild(tdDesc);
    tr.appendChild(tdTempo);
    tr.appendChild(tdTags);
    tr.appendChild(tdAcoes);
    return tr;
  }

  function autoGrow(textarea) {
    textarea.style.height = "auto";
    textarea.style.height = textarea.scrollHeight + "px";
  }

  // ======= Ações =======
  function addItem() {
    if (itens.length >= MAX_ITENS) {
      alert("Limite de 10 itens atingido.");
      return;
    }
    itens.push({ descricao: "", tempo_seg: null, ncr_tags: [] });
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
      if (!it.descricao || !it.descricao.trim()) errors.push(`Item ${idx + 1}: descrição vazia.`);
      if (!Number.isFinite(it.tempo_seg) || it.tempo_seg <= 0) errors.push(`Item ${idx + 1}: informe o tempo estimado (s) > 0.`);
    });

    if (errors.length) {
      alert(errors.join("\n"));
      return null;
    }

    // JSON padronizado com o backend
    return {
      modelo,
      items: itens.map((it, i) => ({
        ordem: i + 1,
        descricao: it.descricao.trim(),
        tempo_seg: it.tempo_seg,
        ncr_tags: it.ncr_tags.slice(0, 12)
      }))
    };
  }

  // ======= Integração com Backend =======
  async function salvarNoSistema() {
    const payload = montarPayload();
    if (!payload) return;

    try {
      const resp = await fetch("/api/gp/checklist/template", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload)
      });
      const data = await resp.json();
      if (!resp.ok || !data.ok) {
        throw new Error(data.error || "Falha ao salvar.");
      }
      alert("Checklist salvo no sistema para o modelo: " + payload.modelo);
    } catch (err) {
      console.error(err);
      alert("Erro ao salvar: " + err.message);
    }
  }

  async function abrirDoSistema() {
    const modelo = selModelo.value || "";
    if (!modelo) { alert("Selecione o modelo para abrir."); return; }

    try {
      const resp = await fetch(`/api/gp/checklist/template/${encodeURIComponent(modelo)}`);
      const data = await resp.json();
      if (!resp.ok || !data.ok) {
        throw new Error(data.error || "Falha ao carregar.");
      }
      aplicarDoServidor(data.data);
    } catch (err) {
      console.error(err);
      alert("Erro ao abrir: " + err.message);
    }
  }

  function aplicarDoServidor(template) {
    // template = { id, modelo, items:[{ordem, descricao, tempo_seg, ncr_tags}], ... }
    itens = (template.items || []).slice(0, MAX_ITENS).map(it => ({
      descricao: it.descricao || "",
      tempo_seg: Number.isFinite(parseInt(it.tempo_seg, 10)) ? parseInt(it.tempo_seg, 10) : null,
      ncr_tags: Array.isArray(it.ncr_tags) ? it.ncr_tags.slice(0, 12) : []
    }));
    if (!MODELOS.includes(template.modelo) && template.modelo) {
      // se vier um modelo desconhecido do BD, tenta selecionar mesmo assim adicionando-o ao select
      const opt = document.createElement("option");
      opt.value = template.modelo; opt.textContent = template.modelo;
      selModelo.appendChild(opt);
    }
    if (template.modelo) selModelo.value = template.modelo;
    if (itens.length === 0) addItem();
    render();
  }

  // Start
  init();
})();
