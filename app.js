const products = [
  { id: 1, model: "iPhone 16 Pro Max", series: "iPhone 16", storage: 256, color: "Натуральный титан", price: 139990, oldPrice: 149990, badge: "Новинка", badgeType: "new", stock: true, rank: 10, year: 2025, image: "assets/products/iphone-16-pro-hero.jpg", bg: "#050505", darkImage: true },
  { id: 2, model: "iPhone 16 Pro", series: "iPhone 16", storage: 256, color: "Пустынный титан", price: 119990, badge: "Хит", badgeType: "sale", stock: true, rank: 9, year: 2025, image: "assets/products/iphone-16-pro.jpg", bg: "#050505", darkImage: true },
  { id: 3, model: "iPhone 16", series: "iPhone 16", storage: 128, color: "Ультрамарин", price: 84990, badge: "Новинка", badgeType: "new", stock: true, rank: 8, year: 2025, image: "assets/products/iphone-16.jpg", bg: "#f5f5f7" },
  { id: 4, model: "iPhone 15 Pro Max", series: "iPhone 15", storage: 256, color: "Синий титан", price: 119990, oldPrice: 129990, badge: "−8%", badgeType: "sale", stock: true, rank: 7, year: 2024, image: "assets/products/iphone-15-pro.jpg", bg: "#f5f5f7" },
  { id: 5, model: "iPhone 15", series: "iPhone 15", storage: 128, color: "Розовый", price: 72990, badge: "Хит", badgeType: "sale", stock: true, rank: 10, year: 2024, image: "assets/products/iphone-15.jpg", bg: "#f5f5f7" },
  { id: 6, model: "iPhone 15 Plus", series: "iPhone 15", storage: 256, color: "Зелёный", price: 89990, stock: false, rank: 4, year: 2024, image: "assets/products/iphone-15.jpg", bg: "#f5f5f7" },
  { id: 7, model: "iPhone 14", series: "iPhone 14", storage: 128, color: "Голубой", price: 61990, oldPrice: 69990, badge: "−11%", badgeType: "sale", stock: true, rank: 6, year: 2023, image: "assets/products/iphone-14.jpg", bg: "#f5f5f7", darkImage: true },
  { id: 8, model: "iPhone 14 Plus", series: "iPhone 14", storage: 256, color: "Фиолетовый", price: 76990, stock: true, rank: 5, year: 2023, image: "assets/products/iphone-14.jpg", bg: "#f5f5f7", darkImage: true },
  { id: 9, model: "iPhone 13", series: "iPhone 13", storage: 128, color: "Тёмная ночь", price: 54990, badge: "Выгодно", badgeType: "sale", stock: true, rank: 8, year: 2022, image: "assets/products/iphone-13.jpg", bg: "#f5f5f7" }
];

const state = {
  models: new Set(),
  storages: new Set(),
  priceMin: 0,
  priceMax: 160000,
  stockOnly: false,
  search: "",
  sort: "popular",
  cart: loadCart()
};

function loadCart() {
  try {
    const saved = JSON.parse(localStorage.getItem("ipoint-cart") || "{}");
    return saved && typeof saved === "object" && !Array.isArray(saved) ? saved : {};
  } catch {
    return {};
  }
}

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const money = value => new Intl.NumberFormat("ru-RU").format(value) + " ₽";
const pluralProducts = n => `${n} ${n % 10 === 1 && n % 100 !== 11 ? "товар" : [2,3,4].includes(n % 10) && ![12,13,14].includes(n % 100) ? "товара" : "товаров"}`;
const swatches = { "Натуральный титан": "#b8b1a5", "Пустынный титан": "#c9a98c", "Ультрамарин": "#687dcc", "Синий титан": "#536174", "Розовый": "#e5c4c9", "Зелёный": "#bdcebf", "Голубой": "#abc6d8", "Фиолетовый": "#b7aecb", "Тёмная ночь": "#343941" };

function productImage(product, thumb = false) {
  return `<img class="${thumb ? "cart-product-photo" : "product-photo"} ${product.darkImage ? "dark-photo" : ""}" src="${product.image}" alt="${product.model}" ${thumb ? "" : "loading=\"lazy\""}>`;
}

function setupFilters() {
  const modelCounts = products.reduce((acc, p) => ({ ...acc, [p.series]: (acc[p.series] || 0) + 1 }), {});
  $("#modelFilters").innerHTML = Object.entries(modelCounts).map(([model, count]) => `
    <label class="check-row"><input type="checkbox" name="model" value="${model}"><span>${model}</span><b>${count}</b></label>
  `).join("");

  const storages = [...new Set(products.map(p => p.storage))].sort((a,b) => a-b);
  $("#storageFilters").innerHTML = storages.map(storage => `
    <label class="storage-option"><input type="checkbox" name="storage" value="${storage}"><span>${storage} ГБ</span></label>
  `).join("");

  $$("#modelFilters input, #storageFilters input").forEach(input => input.addEventListener("change", readAndRender));
  ["#priceMin", "#priceMax"].forEach(id => $(id).addEventListener("change", readAndRender));
  $("#priceRange").addEventListener("input", event => { $("#priceMax").value = event.target.value; readAndRender(); });
  $("#stockOnly").addEventListener("change", readAndRender);
  $$(".filter-title").forEach(button => button.addEventListener("click", () => {
    const open = button.getAttribute("aria-expanded") === "true";
    button.setAttribute("aria-expanded", String(!open));
    $("span", button).textContent = open ? "+" : "−";
  }));
}

function readAndRender() {
  state.models = new Set($$('input[name="model"]:checked').map(i => i.value));
  state.storages = new Set($$('input[name="storage"]:checked').map(i => Number(i.value)));
  state.priceMin = Math.max(0, Number($("#priceMin").value) || 0);
  state.priceMax = Math.max(state.priceMin, Number($("#priceMax").value) || 160000);
  state.stockOnly = $("#stockOnly").checked;
  renderProducts();
}

function getFilteredProducts() {
  const query = state.search.toLowerCase().trim();
  const filtered = products.filter(product =>
    (!state.models.size || state.models.has(product.series)) &&
    (!state.storages.size || state.storages.has(product.storage)) &&
    product.price >= state.priceMin && product.price <= state.priceMax &&
    (!state.stockOnly || product.stock) &&
    (!query || `${product.model} ${product.storage} ${product.color}`.toLowerCase().includes(query))
  );
  const sorts = {
    popular: (a,b) => b.rank - a.rank,
    "price-asc": (a,b) => a.price - b.price,
    "price-desc": (a,b) => b.price - a.price,
    newest: (a,b) => b.year - a.year
  };
  return filtered.sort(sorts[state.sort]);
}

function renderProducts() {
  const list = getFilteredProducts();
  $("#productCount").textContent = pluralProducts(list.length);
  $("#productGrid").innerHTML = list.map((product, index) => `
    <article class="product-card" style="animation-delay:${Math.min(index * 40, 240)}ms">
      ${product.badge ? `<span class="product-badge ${product.badgeType || ""}">${product.badge}</span>` : ""}
      <div class="product-visual ${product.darkImage ? "dark-visual" : ""}" style="--product-bg:${product.bg}">${productImage(product)}</div>
      <div class="product-info">
        <p class="product-series">Apple · ${product.storage} ГБ</p>
        <h3>${product.model} ${product.storage} ГБ</h3>
        <div class="color-row">
          <i class="color-dot" style="--dot:${swatches[product.color] || "#9ea5ae"}"></i>
          <small>${product.color}</small>
        </div>
        <div class="product-buy">
          <div class="price"><strong>${money(product.price)}</strong><span>от ${money(Math.round(product.price / 24))} / мес.</span></div>
          <button class="add-to-cart ${state.cart[product.id] ? "added" : ""}" type="button" data-add="${product.id}" aria-label="Добавить ${product.model} в корзину">
            <svg aria-hidden="true"><use href="#icon-bag"></use></svg><span>${state.cart[product.id] ? "Добавлено" : "В корзину"}</span>
          </button>
        </div>
      </div>
    </article>
  `).join("");
  $("#emptyState").hidden = list.length > 0;
  renderActiveFilters();
}

function renderActiveFilters() {
  const chips = [];
  state.models.forEach(value => chips.push({ label: value, type: "model", value }));
  state.storages.forEach(value => chips.push({ label: `${value} ГБ`, type: "storage", value }));
  if (state.stockOnly) chips.push({ label: "В наличии", type: "stock", value: true });
  if (state.priceMin > 0 || state.priceMax < 160000) chips.push({ label: `${money(state.priceMin)} — ${money(state.priceMax)}`, type: "price", value: true });
  $("#activeFilters").innerHTML = chips.map(chip => `<button class="filter-chip" data-filter-type="${chip.type}" data-filter-value="${chip.value}">${chip.label}<span>×</span></button>`).join("");
}

function removeFilter(type, value) {
  if (type === "model") $(`input[name="model"][value="${CSS.escape(value)}"]`).checked = false;
  if (type === "storage") $(`input[name="storage"][value="${value}"]`).checked = false;
  if (type === "stock") $("#stockOnly").checked = false;
  if (type === "price") { $("#priceMin").value = 0; $("#priceMax").value = 160000; $("#priceRange").value = 160000; }
  readAndRender();
}

function resetFilters() {
  $$('#filtersPanel input[type="checkbox"]').forEach(i => i.checked = false);
  $("#priceMin").value = 0;
  $("#priceMax").value = 160000;
  $("#priceRange").value = 160000;
  $("#searchInput").value = "";
  state.search = "";
  readAndRender();
}

function saveCart() {
  try {
    localStorage.setItem("ipoint-cart", JSON.stringify(state.cart));
  } catch {
    // Корзина продолжит работать до перезагрузки, даже если хранилище браузера отключено.
  }
}

function addToCart(id) {
  state.cart[id] = (state.cart[id] || 0) + 1;
  saveCart();
  renderCart();
  renderProducts();
  openCart();
}

function updateQuantity(id, delta) {
  const next = (state.cart[id] || 0) + delta;
  if (next <= 0) delete state.cart[id]; else state.cart[id] = next;
  saveCart();
  renderCart();
  renderProducts();
}

function renderCart() {
  const entries = Object.entries(state.cart).filter(([id, count]) => products.some(p => p.id === Number(id)) && count > 0);
  const count = entries.reduce((sum, [, qty]) => sum + qty, 0);
  const total = entries.reduce((sum, [id, qty]) => sum + products.find(p => p.id === Number(id)).price * qty, 0);
  $(".cart-count").textContent = count;
  $("#cartTitleCount").textContent = count;
  $("#cartItems").innerHTML = entries.map(([id, qty]) => {
    const p = products.find(product => product.id === Number(id));
    return `<article class="cart-item">
      <div class="cart-item-visual ${p.darkImage ? "dark-visual" : ""}" style="--product-bg:${p.bg}">${productImage(p, true)}</div>
      <div class="cart-item-details">
        <h3>${p.model}</h3><span>${p.storage} ГБ · ${p.color}</span>
        <div class="quantity"><button type="button" data-qty="-1" data-id="${p.id}" aria-label="Уменьшить количество">−</button><span>${qty}</span><button type="button" data-qty="1" data-id="${p.id}" aria-label="Увеличить количество">+</button></div>
      </div>
      <div class="cart-item-end"><strong>${money(p.price * qty)}</strong><button class="remove-item" type="button" data-remove="${p.id}" aria-label="Удалить ${p.model}"><svg aria-hidden="true"><use href="#icon-trash"></use></svg></button></div>
    </article>`;
  }).join("");
  $("#cartEmpty").hidden = entries.length > 0;
  $("#cartFooter").hidden = entries.length === 0;
  $("#cartSubtotal").textContent = money(total);
  $("#cartTotal").textContent = money(total);
}

function openCart() {
  $("#cartDrawer").classList.add("open");
  $("#cartDrawer").setAttribute("aria-hidden", "false");
  $("#overlay").classList.add("open");
  document.body.classList.add("locked");
}

function closePanels() {
  $("#cartDrawer").classList.remove("open");
  $("#cartDrawer").setAttribute("aria-hidden", "true");
  $("#filtersPanel").classList.remove("open");
  $("#overlay").classList.remove("open");
  document.body.classList.remove("locked");
}

let toastTimer;
function showToast() {
  clearTimeout(toastTimer);
  $("#toast").classList.add("show");
  toastTimer = setTimeout(() => $("#toast").classList.remove("show"), 1800);
}

setupFilters();
renderProducts();
renderCart();

$("#searchInput").addEventListener("input", event => { state.search = event.target.value; renderProducts(); });
$("#sortSelect").addEventListener("change", event => { state.sort = event.target.value; renderProducts(); });
$("#resetFilters").addEventListener("click", resetFilters);
$("#emptyReset").addEventListener("click", resetFilters);
$("#activeFilters").addEventListener("click", event => {
  const chip = event.target.closest(".filter-chip");
  if (chip) removeFilter(chip.dataset.filterType, chip.dataset.filterValue);
});
$("#productGrid").addEventListener("click", event => {
  const button = event.target.closest("[data-add]");
  if (button) addToCart(Number(button.dataset.add));
});
$("#cartItems").addEventListener("click", event => {
  const qty = event.target.closest("[data-qty]");
  const remove = event.target.closest("[data-remove]");
  if (qty) updateQuantity(Number(qty.dataset.id), Number(qty.dataset.qty));
  if (remove) updateQuantity(Number(remove.dataset.remove), -Infinity);
});
$(".cart-button").addEventListener("click", openCart);
$$('.close-cart').forEach(button => button.addEventListener("click", closePanels));
$("#overlay").addEventListener("click", closePanels);
$(".search-trigger").addEventListener("click", () => { $("#catalog").scrollIntoView(); setTimeout(() => $("#searchInput").focus(), 450); });
$("#mobileFilterButton").addEventListener("click", () => { $("#filtersPanel").classList.add("open"); $("#overlay").classList.add("open"); document.body.classList.add("locked"); });
$("#closeFilters").addEventListener("click", closePanels);
$("#applyFilters").addEventListener("click", closePanels);
document.addEventListener("keydown", event => { if (event.key === "Escape") closePanels(); });
$(".checkout-button").addEventListener("click", () => {
  $(".checkout-button").textContent = "Заказ принят — скоро позвоним";
  $(".checkout-button").disabled = true;
});
