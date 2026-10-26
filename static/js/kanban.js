// Kanban: arrastar um cartão (ou escolher no seletor dele) muda o status do item.
(function () {
  const kanban = document.getElementById("kanban");
  if (!kanban) return;
  const csrf = JSON.parse(document.body.getAttribute("hx-headers"))["X-CSRFToken"];
  let arrastando = null;

  function atualizarContadores() {
    kanban.querySelectorAll(".raia").forEach(function (raia) {
      raia.querySelector(".contador").textContent = raia.querySelectorAll(".cartao-item").length;
    });
  }

  function mover(cartao, raia) {
    const valor = raia.dataset.valor;
    const origem = cartao.parentElement;
    raia.querySelector(".raia-itens").appendChild(cartao);
    cartao.querySelector("select.mover").value = valor;
    atualizarContadores();
    fetch(cartao.dataset.url, {
      method: "POST",
      headers: { "X-CSRFToken": csrf, "HX-Request": "true" },
      body: new URLSearchParams({ valor: valor }),
    }).then(function (resposta) {
      if (!resposta.ok) throw new Error(resposta.status);
    }).catch(function () {
      origem.appendChild(cartao);
      cartao.querySelector("select.mover").value = origem.closest(".raia").dataset.valor;
      atualizarContadores();
      alert("Não foi possível mover o item. Recarregue a página e tente de novo.");
    });
  }

  kanban.addEventListener("dragstart", function (e) {
    arrastando = e.target.closest(".cartao-item");
    if (arrastando) arrastando.classList.add("arrastando");
  });
  kanban.addEventListener("dragend", function () {
    if (arrastando) arrastando.classList.remove("arrastando");
    arrastando = null;
    kanban.querySelectorAll(".raia.alvo").forEach(function (r) { r.classList.remove("alvo"); });
  });
  kanban.addEventListener("dragover", function (e) {
    const raia = e.target.closest(".raia");
    if (!raia || !arrastando) return;
    e.preventDefault();
    kanban.querySelectorAll(".raia.alvo").forEach(function (r) { if (r !== raia) r.classList.remove("alvo"); });
    raia.classList.add("alvo");
  });
  kanban.addEventListener("drop", function (e) {
    const raia = e.target.closest(".raia");
    if (!raia || !arrastando) return;
    e.preventDefault();
    if (raia !== arrastando.closest(".raia")) mover(arrastando, raia);
  });
  kanban.addEventListener("change", function (e) {
    if (!e.target.matches("select.mover")) return;
    const cartao = e.target.closest(".cartao-item");
    const raia = kanban.querySelector('.raia[data-valor="' + CSS.escape(e.target.value) + '"]');
    if (raia) mover(cartao, raia);
  });
})();
