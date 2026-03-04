// ====================================================================
// [BLOCO] BLOCO_UTIL
// [NOME] IIFE (Immediately Invoked Function Expression)
// [RESPONSABILIDADE] Encapsular escopo do script, inicializar estado e registrar handlers da UI
// ====================================================================
(function () {
  "use strict";

  // ====================================================================
  // [BLOCO] BLOCO_UTIL
  // [NOME] MODELOS
  // [RESPONSABILIDADE] Definir lista fixa de modelos disponíveis no select
  // ====================================================================
  const MODELOS = ["PM700", "PM2100", "PM2200"];
  // ====================================================================
  // [FIM BLOCO] MODELOS
  // ====================================================================

  // ====================================================================
  // [BLOCO] BLOCO_UTIL
  // [NOME] MAX_ITENS
  // [RESPONSABILIDADE] Definir limite máximo de itens de checklist no editor
  // ====================================================================
  const MAX_ITENS = 10;
  // ====================================================================
  // [FIM BLOCO] MAX_ITENS
  // ====================================================================

  // ====================================================================
  // [BLOCO] BLOCO_UTIL
  // [NOME] Referências DOM (select/tabela/botões)
  // [RESPONSABILIDADE] Capturar elementos de UI usados para renderização e ações
  // ====================================================================
  const selModelo = document.getElementById("modeloSel");
  const tbody = document.getElementById("tbody");
  // const btnAddItem = document.getElementById("btnAddItem");
  const btnAddItem2 = document.getElementById("btnAddItem2");
  // const btnLimpar = document.getElementById("btnLimpar");
  // const btnSalvar = document.getElementById("btnSalvar");
  const btnSalvar2 = document.getElementById("btnSalvar2");
  // const btnAbrir = document.getElementById("btnAbrir");
  // ====================================================================
  // [FIM BLOCO] Referências DOM (select/tabela/botões)
  // ====================================================================

  // ====================================================================
  // [BLOCO] BLOCO_UTIL
  // [NOME] itens
  // [RESPONSABILIDADE] Armazenar estado local dos itens do checklist em edição
  // ====================================================================
  let itens = []; 
  // { descricao, tempo_alvo, min, max, bloqueante, exigeNota, ativo }
  // ====================================================================
  // [FIM BLOCO] itens
  // ====================================================================

  // ====================================================================
  // [BLOCO] FUNÇÃO
  // [NOME] init
  // [RESPONSABILIDADE] Inicializar select de modelos, listeners e seleção inicial via URL ou padrão
  // ====================================================================
  function init() {


    // 1. Popular o Select
    selModelo.innerHTML = "";
    if (typeof MODELOS !== 'undefined' && MODELOS.length > 0) {
        MODELOS.forEach(m => {
            const opt = document.createElement("option");
            opt.value = m; 
            opt.textContent = m;
            selModelo.appendChild(opt);
        });
    }

    // 2. Definir o Listener de mudança
    selModelo.addEventListener("change", () => {
        console.log("Mudança detectada para:", selModelo.value);
        abrirDoSistema();
    });

    // 3. Listeners de Botões
    if (document.getElementById('btnSalvar2')) btnSalvar2.addEventListener("click", salvarNoSistema);
    if (document.getElementById('btnAddItem2')) btnAddItem2.addEventListener("click", addItem);

    // 🚀 LÓGICA DE AUTO-ABRIR (CORRIGIDA)
    
    // Captura o modelo da URL (?modelo=XXXX)
    const urlParams = new URLSearchParams(window.location.search);
    const modeloDaUrl = urlParams.get('modelo');

    // Verifica se o modelo da URL existe nas opções do select
    let encontrouNaUrl = false;
    if (modeloDaUrl) {
        for (let i = 0; i < selModelo.options.length; i++) {
            if (selModelo.options[i].value === modeloDaUrl) {
                selModelo.selectedIndex = i;
                encontrouNaUrl = true;
                break;
            }
        }
    }

    // Se não achou na URL, mas tem opções, pega a primeira
    if (!encontrouNaUrl && selModelo.options.length > 0) {
        selModelo.selectedIndex = 0;
    }

  }
  // ====================================================================
  // [FIM BLOCO] init
  // ====================================================================

  // ====================================================================
  // [BLOCO] FUNÇÃO
  // [NOME] render
  // [RESPONSABILIDADE] Renderizar tabela de itens a partir do estado local
  // ====================================================================
  function render() {
    tbody.innerHTML = "";
    itens.forEach((it, idx) => {
      tbody.appendChild(renderRow(it, idx));
    });
  }
  // ====================================================================
  // [FIM BLOCO] render
  // ====================================================================

  // ====================================================================
  // [BLOCO] FUNÇÃO
  // [NOME] renderRow
  // [RESPONSABILIDADE] Construir linha da tabela com campos editáveis e ações para um item
  // ====================================================================
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

    // ====================================================================
    // [BLOCO] FUNÇÃO
    // [NOME] numCell
    // [RESPONSABILIDADE] Criar célula numérica vinculada a uma propriedade do item
    // ====================================================================
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
    // ====================================================================
    // [FIM BLOCO] numCell
    // ====================================================================

    // ====================================================================
    // [BLOCO] FUNÇÃO
    // [NOME] chkCell
    // [RESPONSABILIDADE] Criar célula checkbox vinculada a uma propriedade booleana do item
    // ====================================================================
    function chkCell(prop) {
      const td = document.createElement("td");
      const chk = document.createElement("input");
      chk.type = "checkbox"; chk.className = "chk";
      chk.checked = !!item[prop];
      chk.addEventListener("change", () => item[prop] = chk.checked);
      td.appendChild(chk);
      return td;
    }
    // ====================================================================
    // [FIM BLOCO] chkCell
    // ====================================================================

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
  // ====================================================================
  // [FIM BLOCO] renderRow
  // ====================================================================

  // ====================================================================
  // [BLOCO] FUNÇÃO
  // [NOME] addItem
  // [RESPONSABILIDADE] Adicionar novo item ao estado local respeitando limite e re-renderizar
  // ====================================================================
  function addItem() {
    if (itens.length >= MAX_ITENS) {
      alert("Limite de 10 itens atingido.");
      return;
    }
    itens.push({ descricao:"", tempo_alvo:null, min:null, max:null, bloqueante:false, exigeNota:false, ativo:true });
    render();
  }
  // ====================================================================
  // [FIM BLOCO] addItem
  // ====================================================================

  // ====================================================================
  // [BLOCO] FUNÇÃO
  // [NOME] limpar
  // [RESPONSABILIDADE] Limpar itens do checklist mediante confirmação e reiniciar com item padrão
  // ====================================================================
  function limpar() {
    if (!confirm("Limpar todos os itens?")) return;
    itens = [];
    addItem();
  }
  // ====================================================================
  // [FIM BLOCO] limpar
  // ====================================================================

  // ====================================================================
  // [BLOCO] FUNÇÃO
  // [NOME] montarPayload
  // [RESPONSABILIDADE] Validar dados do formulário e montar payload JSON para API de template
  // ====================================================================
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
  // ====================================================================
  // [FIM BLOCO] montarPayload
  // ====================================================================

  // ====================================================================
  // [BLOCO] BLOCO_API
  // [NOME] salvarNoSistema
  // [RESPONSABILIDADE] Enviar payload para API e persistir template de checklist do modelo
  // ====================================================================
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
  // ====================================================================
  // [FIM BLOCO] salvarNoSistema
  // ====================================================================

  // ====================================================================
  // [BLOCO] BLOCO_API
  // [NOME] abrirDoSistema
  // [RESPONSABILIDADE] Buscar template do modelo na API e aplicar no editor
  // ====================================================================
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
  // ====================================================================
  // [FIM BLOCO] abrirDoSistema
  // ====================================================================

  // ====================================================================
  // [BLOCO] FUNÇÃO
  // [NOME] aplicarDoServidor
  // [RESPONSABILIDADE] Normalizar template recebido e atualizar estado local + renderização
  // ====================================================================
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
  // ====================================================================
  // [FIM BLOCO] aplicarDoServidor
  // ====================================================================

  // ====================================================================
  // [BLOCO] BLOCO_UTIL
  // [NOME] Bootstrap do módulo
  // [RESPONSABILIDADE] Executar inicialização do editor no carregamento do script
  // ====================================================================
  init();
  // ====================================================================
  // [FIM BLOCO] Bootstrap do módulo
  // ====================================================================

})();
// ====================================================================
// [FIM BLOCO] IIFE (Immediately Invoked Function Expression)
// ====================================================================

// ====================================================================
// MAPA DO ARQUIVO
// --------------------------------------------------------------------
// BLOCO_UTIL: IIFE (Immediately Invoked Function Expression)
// BLOCO_UTIL: MODELOS
// BLOCO_UTIL: MAX_ITENS
// BLOCO_UTIL: Referências DOM (select/tabela/botões)
// BLOCO_UTIL: itens
// FUNÇÃO: init
// FUNÇÃO: render
// FUNÇÃO: renderRow
// FUNÇÃO: numCell
// FUNÇÃO: chkCell
// FUNÇÃO: addItem
// FUNÇÃO: limpar
// FUNÇÃO: montarPayload
// BLOCO_API: salvarNoSistema
// BLOCO_API: abrirDoSistema
// FUNÇÃO: aplicarDoServidor
// BLOCO_UTIL: Bootstrap do módulo
// ====================================================================