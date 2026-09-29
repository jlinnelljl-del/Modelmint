const state = {
  data: null,
  cart: [],
};

const CART_STORAGE_KEY = "modelmint3d.mockCart";

const app = document.querySelector("#app");
const cartPanel = document.querySelector("#cart-panel");
const cartLines = document.querySelector("#cart-lines");
const cartCount = document.querySelector("#cart-count");
const toast = document.querySelector("#toast");

async function init() {
  state.cart = loadCart();
  renderCart();
  const response = await fetch("/api/storefront");
  state.data = await response.json();
  bindShell();
  renderRoute();
}

function bindShell() {
  document.body.addEventListener("click", (event) => {
    const link = event.target.closest("a[data-link]");
    if (!link) return;
    event.preventDefault();
    history.pushState({}, "", link.getAttribute("href"));
    renderRoute();
  });

  document.querySelector("#close-cart").addEventListener("click", () => toggleCart(false));
  window.addEventListener("popstate", renderRoute);
}

function renderRoute() {
  const path = window.location.pathname;
  document.querySelectorAll("nav a").forEach((link) => {
    link.classList.toggle("active", link.getAttribute("href") === path || (path.startsWith("/shop") && link.getAttribute("href") === "/shop"));
  });

  if (path === "/") renderHome();
  else if (path === "/shop") renderShop();
  else if (path === "/cart") renderCartPage();
  else if (path.startsWith("/shop/")) renderProduct(path.split("/").filter(Boolean)[1]);
  else if (path === "/custom-orders") renderCustomOrders();
  else if (path === "/business") renderBusiness();
  else if (path === "/events") renderEvents();
  else if (path === "/new") renderNew();
  else if (path === "/about") renderAbout();
  else if (path === "/contact") renderContact();
  else if (path === "/dev/shopify-status") renderShopifyStatus();
  else renderNotFound();

  app.focus();
}

function renderHome() {
  app.innerHTML = `
    <section class="hero">
      <div class="hero-inner">
        <p class="eyebrow">Custom Prints & Creative Fabrication</p>
        <h1>ModelMint3D</h1>
        <p><span class="hero-kicker">Made for gamers, makers & weirdos.</span> Bring ideas to life, one layer at a time with playful prints, tabletop pieces, custom designs, and colorful finished goods.</p>
        <div class="hero-actions">
          <a class="primary-button" href="/shop" data-link>Shop Products</a>
          <a class="secondary-button" href="/custom-orders" data-link>Request a Quote</a>
        </div>
        <div class="brand-strip" aria-label="Featured categories">
          <span>Tabletop</span>
          <span>Decor</span>
          <span>Organizers</span>
          <span>Clickers</span>
          <span>Custom Design</span>
        </div>
      </div>
    </section>
    <section class="page-section">
      <div class="section-heading">
        <h2>Made For The Fun Shelf</h2>
        <a href="/custom-orders" data-link>Start a custom idea</a>
      </div>
      ${CategoryGrid()}
    </section>
    <section class="page-section">
      <div class="section-heading">
        <h2>Featured Products</h2>
        <a href="/shop" data-link>View shop</a>
      </div>
      ${ProductGrid(state.data.products.slice(0, 4))}
    </section>
    <section class="page-section content-grid">
      ${InfoCard("Print, design, create", "A light creative studio for finished products, custom design work, and small-batch ideas.")}
      ${InfoCard("Color intent, not SKUs", "Pick a vibe like Galaxy, Pastel, Forest, or Artist Choice without needing to know filament names.")}
      ${InfoCard("Custom without chaos", "Coasters, tags, favors, and keepsakes start with a quote request so every order gets reviewed.")}
    </section>
  `;
}

function renderShop() {
  app.innerHTML = `
    <section class="page-section page-title">
      <p class="eyebrow">Shop</p>
      <h1>Curated 3D Printed Products</h1>
      <p>Bright gifts, collectibles, tabletop pieces, and customizable products with finish rules built into the ordering flow.</p>
    </section>
    <section class="page-section">${ProductGrid(state.data.products)}</section>
  `;
}

function renderProduct(handle) {
  const product = state.data.products.find((item) => item.handle === handle);
  if (!product) {
    renderNotFound();
    return;
  }

  app.innerHTML = `
    <section class="page-section page-title">
      <p class="eyebrow">${escapeHtml(product.category)}</p>
      <h1>${escapeHtml(product.title)}</h1>
      <p>${escapeHtml(product.description)}</p>
    </section>
    <section class="page-section product-layout">
      <div class="product-hero"><img src="${product.images[0]}" alt=""></div>
      <article class="detail-card">
        <h2>${escapeHtml(product.title)}</h2>
        <p class="price">$${escapeHtml(product.price)}</p>
        <p class="muted">${escapeHtml(product.product_type)} - ${escapeHtml(product.license_status)}</p>
        ${ProductRuleNotice(product)}
        ${ProductDetailForm(product)}
      </article>
    </section>
  `;

  const form = document.querySelector("#product-form");
  form.addEventListener("submit", (event) => addConfiguredProduct(event, product));
}

function ProductDetailForm(product) {
  const slots = [];
  for (let index = 1; index <= product.color_slot_count; index += 1) {
    slots.push(`
      <label>Color ${index}
        <select name="Color ${index}">${state.data.color_intents.map((intent) => `<option>${escapeHtml(intent)}</option>`).join("")}</select>
      </label>
    `);
  }

  const finishOptions = product.allowed_finishes
    .filter((finish) => !product.blocked_finishes.includes(finish))
    .map((finish) => `<option value="${escapeAttribute(finish)}">${escapeHtml(titleCase(finish))}</option>`)
    .join("");

  return `
    <form id="product-form" class="form-grid">
      ${product.customizable && slots.length ? `<div class="two-col">${slots.join("")}</div>` : ""}
      <label>Finish Preference
        <select name="finish_preference">${finishOptions}</select>
      </label>
      <label>Custom Notes
        <textarea name="Customer Notes" placeholder="Broad color notes, event date, or artist-choice direction"></textarea>
      </label>
      <button class="primary-button" type="submit">${product.customizable ? "Build Order" : "Add to Mock Cart"}</button>
    </form>
  `;
}

function ProductRuleNotice(product) {
  const blocked = product.blocked_finishes.map((finish) => `<span class="chip">${escapeHtml(titleCase(finish))}</span>`).join("");
  return `
    <div class="rule-notice">
      <strong>Finish rules apply</strong>
      <p class="rule-copy">${escapeHtml(product.material_notes)}</p>
      <div class="chip-list">${blocked || '<span class="chip">No blocked finishes</span>'}</div>
    </div>
  `;
}

async function addConfiguredProduct(event, product) {
  event.preventDefault();
  const selections = Object.fromEntries(new FormData(event.currentTarget).entries());
  const response = await fetch("/api/cart-lines", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ handle: product.handle, selections }),
  });

  if (!response.ok) {
    showToast("That finish is not available for this product.");
    return;
  }

  const result = await response.json();
  state.cart.push(result.cart_line);
  saveCart();
  renderCart();
  showToast("Mock order added to cart.");
  history.pushState({}, "", "/cart");
  renderRoute();
}

function renderCartPage() {
  const lines = CartLineList("full");
  app.innerHTML = `
    <section class="page-section page-title">
      <p class="eyebrow">Mock Cart</p>
      <h1>Order Summary</h1>
      <p>This local cart proves customization data before Shopify integration. No payment, taxes, shipping, or checkout happen here.</p>
    </section>
    <section class="page-section">
      <div class="detail-card">
        <div class="rule-notice">
          <strong>Mock cart is local only</strong>
          <p class="rule-copy">Shopify checkout requires configured Storefront API credentials and real test product variant IDs. TODO placeholders are blocked before any Shopify checkout attempt.</p>
        </div>
        ${lines || '<p class="muted">Your mock cart is empty. Build an item from the shop to test the customization flow.</p>'}
        <div id="shopify-proof-result" class="rule-notice" hidden></div>
        <div class="button-row">
          <a class="primary-button" href="/shop" data-link>Continue Shopping</a>
          <button class="secondary-button" type="button" id="shopify-proof" ${state.cart.length ? "" : "disabled"}>Create Shopify Checkout</button>
          <button class="secondary-button" type="button" id="clear-cart">Clear Mock Cart</button>
        </div>
      </div>
    </section>
  `;

  const clearButton = document.querySelector("#clear-cart");
  if (clearButton) {
    clearButton.addEventListener("click", () => {
      state.cart = [];
      saveCart();
      renderCart();
      renderCartPage();
      showToast("Mock cart cleared.");
    });
  }

  const shopifyProofButton = document.querySelector("#shopify-proof");
  if (shopifyProofButton) {
    shopifyProofButton.addEventListener("click", createShopifyCheckoutProof);
  }
}

async function renderShopifyStatus() {
  app.innerHTML = `
    <section class="page-section page-title">
      <p class="eyebrow">Developer status</p>
      <h1>Shopify Connection</h1>
      <p>Server-side proof status. Storefront tokens are never shown in the browser.</p>
    </section>
    <section class="page-section">
      <div class="detail-card" id="shopify-status-panel"><p class="muted">Checking Shopify setup...</p></div>
    </section>
  `;

  const panel = document.querySelector("#shopify-status-panel");
  try {
    const response = await fetch("/api/shopify/status");
    const status = await response.json();
    const products = status.products
      .map(
        (product) => `
          <article class="cart-line">
            <strong>${escapeHtml(product.title || product.handle)}</strong>
            <dl>
              <div><dt>Handle</dt><dd>${escapeHtml(product.handle)}</dd></div>
              <div><dt>Variant</dt><dd>${escapeHtml(product.variant_status)}</dd></div>
              <div><dt>Variant GID</dt><dd>${escapeHtml(product.variant_id || "not shown until configured")}</dd></div>
            </dl>
          </article>
        `,
      )
      .join("");
    panel.innerHTML = `
      <div class="rule-notice">
        <strong>${status.configured ? "Shopify env vars present" : "Shopify env vars missing"}</strong>
        <p class="rule-copy">${escapeHtml(status.message || "Ready for one-product cartCreate proof.")}</p>
      </div>
      <dl class="status-list">
        <div><dt>Store domain</dt><dd>${escapeHtml(status.store_domain || "not configured")}</dd></div>
        <div><dt>API version</dt><dd>${escapeHtml(status.api_version || "not configured")}</dd></div>
        <div><dt>Token visible</dt><dd>${status.token_visible ? "yes - fix this" : "no"}</dd></div>
      </dl>
      <h2>Sample Product Variant Mapping</h2>
      ${products}
    `;
  } catch {
    panel.innerHTML = `<p class="muted">Could not load Shopify status.</p>`;
  }
}

async function createShopifyCheckoutProof() {
  if (!state.cart.length) return;

  const resultBox = document.querySelector("#shopify-proof-result");
  const firstLine = state.cart[0];
  const response = await fetch("/api/shopify/cart/create", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ handle: firstLine.product_handle, selections: firstLine.selections || {} }),
  });
  const result = await response.json();
  resultBox.hidden = false;

  if (!response.ok || !result.ok) {
    resultBox.innerHTML = `<strong>Shopify proof not connected yet</strong><p class="rule-copy">${escapeHtml(result.error || "Shopify checkout is unavailable.")}</p>`;
    return;
  }

  resultBox.innerHTML = `<strong>Shopify checkout URL created</strong><p><a href="${escapeAttribute(result.checkoutUrl)}">${escapeHtml(result.checkoutUrl)}</a></p>`;
}

function renderCustomOrders() {
  app.innerHTML = `
    <section class="page-section page-title">
      <p class="eyebrow">Quote requests</p>
      <h1>Custom and Batch Orders</h1>
      <p>For branded coasters, restaurant tabletop products, event tags, sports teams, party favors, and custom text pieces.</p>
    </section>
    <section class="page-section quote-layout">
      <form id="quote-form" class="quote-form form-grid">
        <div class="two-col">
          <label>Name<input name="customer_name" required></label>
          <label>Email<input name="email" type="email" required></label>
        </div>
        <div class="two-col">
          <label>Phone optional<input name="phone"></label>
          <label>Business/Event Name<input name="business_event_name" required></label>
        </div>
        <div class="two-col">
          <label>Order Type<select name="order_type" required>${state.data.quote_order_types.map((item) => `<option>${escapeHtml(item)}</option>`).join("")}</select></label>
          <label>Target Quantity<input name="target_quantity" type="number" min="1" required></label>
        </div>
        <div class="two-col">
          <label>Deadline<input name="deadline" type="date" required></label>
          <label>Budget Range optional<input name="budget_range" placeholder="$100-$300"></label>
        </div>
        <label>Logo/Artwork Note optional<input name="logo_artwork_note" placeholder="Tell us what file you can provide"></label>
        <label>Notes<textarea name="notes" required placeholder="Size, colors, audience, pickup timing, or constraints"></textarea></label>
        <label>Pickup/Shipping Preference<select name="fulfillment_preference" required><option>Local pickup</option><option>Shipping quote needed</option><option>Not sure yet</option></select></label>
        <button class="primary-button" type="submit">Submit Quote Request</button>
      </form>
      <aside class="info-card">
        <h3>Review first</h3>
        <p class="muted">Custom and batch requests create quote records. They are not instant checkout orders.</p>
        <p class="muted">The next step is review, quote, customer approval, then production.</p>
      </aside>
    </section>
  `;
  document.querySelector("#quote-form").addEventListener("submit", submitQuote);
}

async function submitQuote(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const payload = Object.fromEntries(new FormData(form).entries());
  const response = await fetch("/api/quote-requests", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    showToast("Please check the required quote fields.");
    return;
  }

  form.reset();
  showToast("Quote request saved for review.");
}

function renderBusiness() {
  renderSimplePage("Business Orders", "This will become the more polished commercial side for branded coasters, tabletop products, venues, events, and batch orders. For now, it stays separate from the cute consumer shop.", [
    "Commercial subsite placeholder",
    "Branded coaster sets",
    "Venue and event batches",
  ]);
}

function renderEvents() {
  renderSimplePage("Events", "Upcoming craft fairs, market dates, and pickup windows will appear here.", ["Calendar placeholder", "Market product previews", "Local pickup notes"]);
}

function renderNew() {
  renderSimplePage("New Arrivals", "A future feed for newly approved products and newsletter candidates.", state.data.products.map((product) => product.title));
}

function renderAbout() {
  renderSimplePage("About ModelMint3D", "A creative fabrication shop for playful prints, tabletop pieces, useful little objects, custom gifts, and small-batch ideas.", ["Print", "Design", "Create"]);
}

function renderContact() {
  renderSimplePage("Contact", "Use the custom order form for quote requests. General contact details can be added here before launch.", ["Custom quote form", "Local pickup questions", "Business product inquiries"]);
}

function renderSimplePage(title, copy, items) {
  app.innerHTML = `
    <section class="page-section page-title">
      <p class="eyebrow">ModelMint</p>
      <h1>${escapeHtml(title)}</h1>
      <p>${escapeHtml(copy)}</p>
    </section>
    <section class="page-section content-grid">
      ${items.map((item) => InfoCard(item, "Placeholder content for Website-1.")).join("")}
    </section>
  `;
}

function renderNotFound() {
  app.innerHTML = `
    <section class="page-section page-title">
      <p class="eyebrow">Not found</p>
      <h1>That page is not available.</h1>
      <p>Return to the catalog or request a custom quote.</p>
      <div class="button-row"><a class="primary-button" href="/shop" data-link>Shop</a></div>
    </section>
  `;
}

function ProductGrid(products) {
  return `
    <div class="product-grid">
      ${products.map(ProductCard).join("")}
    </div>
  `;
}

function CategoryGrid() {
  const categories = [
    ["Tabletop", "Dice towers, accessories, and fantasy-table energy."],
    ["Decor", "Dragons, display pieces, HueForge-style art, and shelf magic."],
    ["Organizers", "Useful printed parts for desks, tables, craft setups, and shops."],
    ["Clickers", "Fidgety, tactile, pocketable things for tiny dopamine moments."],
    ["Custom Design", "Coasters, tags, gifts, names, logos, and weird little ideas."],
  ];

  return `
    <div class="category-grid">
      ${categories
        .map(
          ([title, copy]) => `
            <a class="category-card" href="${title === "Custom Design" ? "/custom-orders" : "/shop"}" data-link>
              <h3>${escapeHtml(title)}</h3>
              <p class="muted">${escapeHtml(copy)}</p>
            </a>
          `,
        )
        .join("")}
    </div>
  `;
}

function ProductCard(product) {
  return `
    <a class="product-card" href="/shop/${product.handle}" data-link>
      <div class="product-card-media"><img src="${product.images[0]}" alt=""></div>
      <div class="product-card-body">
        <h3>${escapeHtml(product.title)}</h3>
        <p class="muted">${escapeHtml(product.category)}</p>
        <p class="price">$${escapeHtml(product.price)}</p>
      </div>
    </a>
  `;
}

function InfoCard(title, copy) {
  return `<article class="info-card"><h3>${escapeHtml(title)}</h3><p class="muted">${escapeHtml(copy)}</p></article>`;
}

function toggleCart(open) {
  cartPanel.classList.toggle("open", open);
  cartPanel.setAttribute("aria-hidden", open ? "false" : "true");
}

function renderCart() {
  cartCount.textContent = state.cart.length;
  if (!state.cart.length) {
    cartLines.innerHTML = `<p class="muted">Your sample cart is empty.</p>`;
    return;
  }

  cartLines.innerHTML = CartLineList("panel");
}

function CartLineList(mode) {
  if (!state.cart.length) return "";
  return state.cart
    .map((line) => {
      const attrs = Object.entries(line.line_item_attributes || {})
        .map(([key, value]) => `<div><dt>${escapeHtml(key)}</dt><dd>${escapeHtml(value)}</dd></div>`)
        .join("");
      const image = mode === "full" && line.image ? `<img src="${escapeAttribute(line.image)}" alt="">` : "";
      return `<article class="cart-line ${mode === "full" ? "cart-line-full" : ""}">${image}<div><strong>${escapeHtml(line.title)} - $${escapeHtml(line.price)}</strong><dl>${attrs}</dl></div></article>`;
    })
    .join("");
}

function loadCart() {
  try {
    const parsed = JSON.parse(sessionStorage.getItem(CART_STORAGE_KEY) || "[]");
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveCart() {
  sessionStorage.setItem(CART_STORAGE_KEY, JSON.stringify(state.cart));
}

function showToast(message) {
  toast.textContent = message;
  toast.classList.add("visible");
  setTimeout(() => toast.classList.remove("visible"), 2200);
}

function titleCase(value) {
  return String(value).replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeAttribute(value) {
  return escapeHtml(value).replaceAll("`", "&#096;");
}

init().catch(() => showToast("Could not load storefront."));
