const state = {
  // Estado compartido de la pantalla. Se mantiene en memoria porque el MVP no
  // necesita framework ni almacenamiento cliente para la demo.
  options: null,
  exerciseFilters: null,
  users: [],
  routine: null,
  catalog: [],
  catalogLimit: 30,
  catalogTotal: 0,
  activity: [],
  // Evita pintar una respuesta antigua si el usuario cambia de perfil mientras
  // se esta cargando el historial.
  historyRequestId: 0,
};

const PROVINCES = [
  "A Coruña",
  "Álava",
  "Albacete",
  "Alicante",
  "Almería",
  "Asturias",
  "Ávila",
  "Badajoz",
  "Barcelona",
  "Burgos",
  "Cáceres",
  "Cádiz",
  "Cantabria",
  "Castellón",
  "Ceuta",
  "Ciudad Real",
  "Córdoba",
  "Cuenca",
  "Girona",
  "Granada",
  "Guadalajara",
  "Gipuzkoa",
  "Huelva",
  "Huesca",
  "Illes Balears",
  "Jaén",
  "La Rioja",
  "Las Palmas",
  "León",
  "Lleida",
  "Lugo",
  "Madrid",
  "Málaga",
  "Melilla",
  "Murcia",
  "Navarra",
  "Ourense",
  "Palencia",
  "Pontevedra",
  "Salamanca",
  "Santa Cruz de Tenerife",
  "Segovia",
  "Sevilla",
  "Soria",
  "Tarragona",
  "Teruel",
  "Toledo",
  "Valencia",
  "Valladolid",
  "Bizkaia",
  "Zamora",
  "Zaragoza",
];

const els = {
  apiState: document.querySelector("#apiState"),
  profileForm: document.querySelector("#profileForm"),
  userSelect: document.querySelector("#userSelect"),
  provinceSelect: document.querySelector("#provinceSelect"),
  objectiveSelect: document.querySelector("#objectiveSelect"),
  levelSelect: document.querySelector("#levelSelect"),
  environmentSelect: document.querySelector("#environmentSelect"),
  minutesRange: document.querySelector("#minutesRange"),
  minutesLabel: document.querySelector("#minutesLabel"),
  routineSummary: document.querySelector("#routineSummary"),
  routineList: document.querySelector("#routineList"),
  routineEmpty: document.querySelector("#routineEmpty"),
  reloadHistory: document.querySelector("#reloadHistory"),
  exerciseSearch: document.querySelector("#exerciseSearch"),
  catalogEnvironmentFilter: document.querySelector("#catalogEnvironmentFilter"),
  categoryFilter: document.querySelector("#categoryFilter"),
  targetFilter: document.querySelector("#targetFilter"),
  equipmentFilter: document.querySelector("#equipmentFilter"),
  sortFilter: document.querySelector("#sortFilter"),
  clearFilters: document.querySelector("#clearFilters"),
  filterChips: document.querySelector("#filterChips"),
  exerciseSelect: document.querySelector("#exerciseSelect"),
  activityMinutes: document.querySelector("#activityMinutes"),
  addActivity: document.querySelector("#addActivity"),
  saveActivity: document.querySelector("#saveActivity"),
  activityList: document.querySelector("#activityList"),
  activityTotal: document.querySelector("#activityTotal"),
  catalogGrid: document.querySelector("#catalogGrid"),
  catalogCount: document.querySelector("#catalogCount"),
  loadMoreExercises: document.querySelector("#loadMoreExercises"),
  routineHistory: document.querySelector("#routineHistory"),
  activityHistory: document.querySelector("#activityHistory"),
  historyDetailTitle: document.querySelector("#historyDetailTitle"),
  historyDetailMeta: document.querySelector("#historyDetailMeta"),
  historyDetailEmpty: document.querySelector("#historyDetailEmpty"),
  historyDetail: document.querySelector("#historyDetail"),
  toast: document.querySelector("#toast"),
};

document.querySelectorAll(".nav-tab").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".nav-tab").forEach((tab) => tab.classList.remove("is-active"));
    document.querySelectorAll(".section").forEach((section) => section.classList.remove("is-visible"));
    button.classList.add("is-active");
    document.querySelector(`#${button.dataset.section}`).classList.add("is-visible");
    if (button.dataset.section === "history") loadHistory();
  });
});

els.minutesRange.addEventListener("input", () => {
  els.minutesLabel.textContent = `${els.minutesRange.value} min`;
});

els.profileForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(els.profileForm).entries());
  data.available_minutes = Number(data.available_minutes);
  data.training_days = Number(data.training_days);
  data.weight = Number(data.weight);
  data.height = Number(data.height || 0) || null;

  try {
    setBusy(true);
    const routine = await api("/api/routines/recommend", {
      method: "POST",
      body: JSON.stringify(data),
    });
    state.routine = routine;
    renderRoutine(routine);
    await loadUsers();
    await loadHistory();
    toast("Rutina generada");
  } catch (error) {
    toast(error.message);
  } finally {
    setBusy(false);
  }
});

els.reloadHistory.addEventListener("click", loadHistory);
els.userSelect.addEventListener("change", applySelectedUser);

els.exerciseSearch.addEventListener("input", debounce(() => loadExercises(), 260));
els.catalogEnvironmentFilter.addEventListener("change", () => loadExercises());
els.categoryFilter.addEventListener("change", () => loadExercises());
els.targetFilter.addEventListener("change", () => loadExercises());
els.equipmentFilter.addEventListener("change", () => loadExercises());
els.sortFilter.addEventListener("change", () => loadExercises());
els.clearFilters.addEventListener("click", clearCatalogFilters);
els.loadMoreExercises.addEventListener("click", () => loadExercises({ append: true }));

els.addActivity.addEventListener("click", () => {
  const selected = state.catalog.find((exercise) => exercise.id === els.exerciseSelect.value);
  const minutes = Number(els.activityMinutes.value);
  addExerciseToActivity(selected, minutes);
});

els.saveActivity.addEventListener("click", async () => {
  if (!state.activity.length) {
    toast("No hay ejercicios registrados");
    return;
  }

  const form = Object.fromEntries(new FormData(els.profileForm).entries());
  try {
    const response = await api("/api/activity", {
      method: "POST",
      body: JSON.stringify({
        username: form.username || "demo",
        email: form.email || null,
        weight: Number(form.weight || 70),
        entries: state.activity.map((item) => ({
          exercise_id: item.exercise.id,
          minutes: item.minutes,
        })),
      }),
    });
    state.activity = [];
    renderActivity();
    await loadUsers();
    await loadHistory();
    toast(`Actividad guardada: ${response.total_calories} kcal`);
  } catch (error) {
    toast(error.message);
  }
});

init();

async function init() {
  try {
    const health = await api("/api/health");
    els.apiState.classList.add("is-ok");
    els.apiState.textContent = `${health.exercise_count} ejercicios`;
  } catch (error) {
    els.apiState.textContent = "API sin conexión";
  }

  try {
    state.options = await api("/api/options");
    fillSelect(els.objectiveSelect, state.options.objectives);
    fillSelect(els.levelSelect, state.options.levels);
    fillSelect(els.environmentSelect, state.options.environments);
    fillProvinceSelect();
    els.objectiveSelect.value = "perdida_grasa";
    els.levelSelect.value = "principiante";
    els.environmentSelect.value = "casa";
    els.provinceSelect.value = "";
  } catch (error) {
    toast(error.message);
  }

  await loadExerciseFilters();
  await loadUsers();
  await loadExercises();
  await loadHistory();
}

async function api(path, options = {}) {
  // Envoltorio unico para que todos los errores de la API se muestren igual.
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || "Error de servidor");
  }
  return response.json();
}

function fillSelect(select, options) {
  select.innerHTML = options
    .map((option) => `<option value="${escapeHtml(option.value)}">${escapeHtml(option.label)}</option>`)
    .join("");
}

function fillProvinceSelect() {
  els.provinceSelect.innerHTML = [
    `<option value="">Selecciona provincia</option>`,
    ...PROVINCES.map((province) => `<option value="${escapeHtml(province)}">${escapeHtml(province)}</option>`),
  ].join("");
}

async function loadUsers() {
  try {
    const currentUsername = new FormData(els.profileForm).get("username") || "";
    const response = await api("/api/users");
    state.users = response.items || [];
    els.userSelect.innerHTML = [
      `<option value="">Nuevo usuario</option>`,
      ...state.users.map((user) => `<option value="${escapeHtml(user.username)}">${escapeHtml(user.label)}</option>`),
    ].join("");
    const current = state.users.find((user) => user.username === String(currentUsername).trim().toLowerCase());
    els.userSelect.value = current ? current.username : "";
    if (!current && !String(currentUsername).trim()) {
      resetNewUserForm({ refreshHistory: false });
    }
  } catch (error) {
    toast(error.message);
  }
}

function applySelectedUser() {
  const username = els.userSelect.value;
  if (!username) {
    resetNewUserForm();
    return;
  }
  const user = state.users.find((item) => item.username === username);
  if (!user) return;

  setField("username", user.username);
  setField("email", user.email || "");
  setField("name", user.name || "");
  setProvince(user.province || "Las Palmas");
  setField("weight", user.weight || 70);
  setField("height", user.height || 170);
  setField("training_days", user.training_days || 3);
  if (user.objective) els.objectiveSelect.value = user.objective;
  if (user.level) els.levelSelect.value = user.level;
  if (user.environment) els.environmentSelect.value = user.environment;
  if (user.available_minutes) {
    els.minutesRange.value = user.available_minutes;
    els.minutesLabel.textContent = `${user.available_minutes} min`;
  }
  resetHistoryDetail();
  loadHistory();
}

function resetNewUserForm({ refreshHistory = true } = {}) {
  setField("username", "");
  setField("email", "");
  setField("name", "");
  els.provinceSelect.value = "";
  setField("weight", 70);
  setField("height", 170);
  setField("training_days", 3);
  els.objectiveSelect.value = "perdida_grasa";
  els.levelSelect.value = "principiante";
  els.environmentSelect.value = "casa";
  els.minutesRange.value = 45;
  els.minutesLabel.textContent = "45 min";
  resetHistoryDetail();
  if (refreshHistory) loadHistory();
}

function setField(name, value) {
  const input = els.profileForm.elements[name];
  if (input) input.value = value;
}

function setProvince(value) {
  if (![...els.provinceSelect.options].some((option) => option.value === value)) {
    els.provinceSelect.add(new Option(value, value));
  }
  els.provinceSelect.value = value;
}

async function loadExerciseFilters() {
  try {
    state.exerciseFilters = await api("/api/exercise-filters");
    fillFilterSelect(els.catalogEnvironmentFilter, null, state.exerciseFilters.environments);
    fillFilterSelect(els.categoryFilter, "Todos los grupos", state.exerciseFilters.categories);
    fillFilterSelect(els.targetFilter, "Todos los músculos", state.exerciseFilters.targets);
    fillFilterSelect(els.equipmentFilter, "Todo equipamiento", state.exerciseFilters.equipment);
  } catch (error) {
    toast(error.message);
  }
}

function fillFilterSelect(select, placeholder, values) {
  const options = placeholder ? [`<option value="">${escapeHtml(placeholder)}</option>`] : [];
  options.push(
    ...values.map((item) => {
      const value = typeof item === "string" ? item : item.value;
      const label = typeof item === "string" ? item : item.label;
      return `<option value="${escapeHtml(value)}">${escapeHtml(label)}</option>`;
    })
  );
  select.innerHTML = options.join("");
}

async function loadExercises({ append = false } = {}) {
  // Los filtros se mandan como query params para que backend y frontend usen la
  // misma fuente de verdad sobre catalogo, paginacion y ordenacion.
  const params = new URLSearchParams();
  const query = els.exerciseSearch.value.trim();
  if (query) params.set("query", query);
  params.set("environment", els.catalogEnvironmentFilter.value || "casa");
  if (els.categoryFilter.value) params.set("category", els.categoryFilter.value);
  if (els.targetFilter.value) params.set("target", els.targetFilter.value);
  if (els.equipmentFilter.value) params.set("equipment", els.equipmentFilter.value);
  if (els.sortFilter.value) params.set("sort", els.sortFilter.value);
  params.set("limit", String(state.catalogLimit));
  params.set("offset", append ? String(state.catalog.length) : "0");

  try {
    const response = await api(`/api/exercises?${params.toString()}`);
    const items = Array.isArray(response) ? response : response.items;
    state.catalog = append ? [...state.catalog, ...items] : items;
    state.catalogTotal = Array.isArray(response) ? state.catalog.length : response.total;
    renderExerciseSelect();
    renderCatalog();
    renderFilterChips();
  } catch (error) {
    toast(error.message);
  }
}

function renderRoutine(routine) {
  els.routineEmpty.style.display = "none";
  els.routineSummary.innerHTML = `
    <div><strong>${routine.exercises.length}</strong><span>ejercicios</span></div>
    <div><strong>${routine.estimated_minutes}</strong><span>minutos</span></div>
    <div><strong>${Math.round(routine.estimated_calories)}</strong><span>kcal</span></div>
  `;
  els.routineList.innerHTML = routine.exercises.map(renderRoutineExercise).join("");
}

function renderRoutineExercise(item) {
  const exercise = item.exercise;
  const instruction = trimText(exercise.instructions || "", 180);
  return `
    <article class="exercise-card">
      <img src="${exercise.image_url || ""}" alt="${escapeHtml(exercise.name)}" loading="lazy" />
      <div>
        <h3>${item.order}. ${escapeHtml(exercise.name)}</h3>
        <div class="meta-row">
          <span class="pill">${escapeHtml(exercise.target)}</span>
          <span class="pill">${escapeHtml(exercise.equipment)}</span>
          <span class="pill coral">${item.sets} x ${escapeHtml(item.reps)}</span>
          <span class="pill">${item.minutes} min</span>
          <span class="pill">${Math.round(item.calories)} kcal</span>
        </div>
        <p>${escapeHtml(instruction)}</p>
      </div>
    </article>
  `;
}

function renderExerciseSelect() {
  if (!state.catalog.length) {
    els.exerciseSelect.innerHTML = `<option value="">Sin resultados</option>`;
    return;
  }
  els.exerciseSelect.innerHTML = state.catalog
    .map((exercise) => `<option value="${exercise.id}">${escapeHtml(exercise.name)}</option>`)
    .join("");
}

function renderCatalog() {
  els.catalogCount.textContent = `${state.catalog.length} de ${state.catalogTotal} ejercicios`;
  els.loadMoreExercises.hidden = state.catalog.length >= state.catalogTotal;
  if (!state.catalog.length) {
    els.catalogGrid.innerHTML = `<div class="empty-state">No hay ejercicios con esos filtros.</div>`;
    return;
  }
  els.catalogGrid.innerHTML = state.catalog
    .map(
      (exercise) => `
        <button class="catalog-card" type="button" data-add-exercise="${exercise.id}">
          <img src="${exercise.image_url || ""}" alt="${escapeHtml(exercise.name)}" loading="lazy" />
          <h3>${escapeHtml(exercise.name)}</h3>
          <div class="meta-row">
            <span class="pill">${escapeHtml(exercise.target)}</span>
            <span class="pill">${escapeHtml(exercise.equipment)}</span>
          </div>
        </button>
      `
    )
    .join("");

  document.querySelectorAll("[data-add-exercise]").forEach((button) => {
    button.addEventListener("click", () => {
      const exercise = state.catalog.find((item) => item.id === button.dataset.addExercise);
      addExerciseToActivity(exercise, Number(els.activityMinutes.value));
    });
  });
}

function renderFilterChips() {
  const chips = [];
  const query = els.exerciseSearch.value.trim();
  if (query) chips.push({ label: `Texto: ${query}`, control: "exerciseSearch" });
  if (els.catalogEnvironmentFilter.value) {
    chips.push({ label: `Entorno: ${selectedLabel(els.catalogEnvironmentFilter)}`, control: "catalogEnvironmentFilter" });
  }
  if (els.categoryFilter.value) chips.push({ label: `Grupo: ${els.categoryFilter.value}`, control: "categoryFilter" });
  if (els.targetFilter.value) chips.push({ label: `Músculo: ${els.targetFilter.value}`, control: "targetFilter" });
  if (els.equipmentFilter.value) chips.push({ label: `Equipo: ${els.equipmentFilter.value}`, control: "equipmentFilter" });
  if (els.sortFilter.value && els.sortFilter.value !== "name") {
    chips.push({ label: `Orden: ${selectedLabel(els.sortFilter)}`, control: "sortFilter" });
  }

  els.filterChips.innerHTML = chips
    .map(
      (chip) => `
        <span class="filter-chip">
          ${escapeHtml(chip.label)}
          ${chip.control ? `<button type="button" data-clear-filter="${chip.control}" aria-label="Quitar filtro">x</button>` : ""}
        </span>
      `
    )
    .join("");

  document.querySelectorAll("[data-clear-filter]").forEach((button) => {
    button.addEventListener("click", () => {
      const control = els[button.dataset.clearFilter];
      control.value = button.dataset.clearFilter === "sortFilter" ? "name" : button.dataset.clearFilter === "catalogEnvironmentFilter" ? "casa" : "";
      loadExercises();
    });
  });
}

function selectedLabel(select) {
  return select.options[select.selectedIndex]?.textContent || select.value;
}

function clearCatalogFilters() {
  els.exerciseSearch.value = "";
  els.catalogEnvironmentFilter.value = "casa";
  els.categoryFilter.value = "";
  els.targetFilter.value = "";
  els.equipmentFilter.value = "";
  els.sortFilter.value = "name";
  loadExercises();
}

function addExerciseToActivity(exercise, minutes) {
  if (!exercise || !minutes || minutes < 1) return;
  state.activity.push({ exercise, minutes });
  renderActivity();
  toast(`${exercise.name} añadido`);
}

function renderActivity() {
  const totalCalories = state.activity.reduce(
    (sum, item) => sum + calories(item.exercise.met_estimate, getWeight(), item.minutes),
    0
  );
  els.activityTotal.textContent = `${Math.round(totalCalories)} kcal`;
  if (!state.activity.length) {
    els.activityList.innerHTML = `<div class="empty-state">Sin actividad registrada.</div>`;
    return;
  }

  els.activityList.innerHTML = state.activity
    .map((item, index) => {
      const kcal = calories(item.exercise.met_estimate, getWeight(), item.minutes);
      return `
        <div class="activity-row">
          <div>
            <strong>${escapeHtml(item.exercise.name)}</strong>
            <span>${item.minutes} min · ${Math.round(kcal)} kcal</span>
          </div>
          <button class="remove-row" type="button" aria-label="Eliminar" data-remove="${index}">x</button>
        </div>
      `;
    })
    .join("");

  document.querySelectorAll("[data-remove]").forEach((button) => {
    button.addEventListener("click", () => {
      state.activity.splice(Number(button.dataset.remove), 1);
      renderActivity();
    });
  });
}

async function loadHistory() {
  // Cada peticion recibe un id incremental; si llega tarde, se descarta para no
  // mezclar historiales entre usuarios.
  const requestId = ++state.historyRequestId;
  const username = getActiveUsername();
  if (!username) {
    renderHistoryLists([], []);
    resetHistoryDetail("Selecciona un usuario");
    return;
  }

  const params = new URLSearchParams();
  params.set("username", username);
  const email = getActiveEmail(username);
  if (email) params.set("email", email);
  try {
    const history = await api(`/api/history?${params.toString()}`);
    if (requestId !== state.historyRequestId || username !== getActiveUsername()) return;
    renderHistoryLists(history.routines, history.activities);
  } catch (error) {
    if (requestId !== state.historyRequestId) return;
    toast(error.message);
  }
}

function getActiveUsername() {
  const selected = String(els.userSelect.value || "").trim().toLowerCase();
  if (selected) return selected;
  return String(new FormData(els.profileForm).get("username") || "").trim().toLowerCase();
}

function getActiveEmail(username) {
  const selectedUser = state.users.find((user) => user.username === username);
  return selectedUser?.email || String(new FormData(els.profileForm).get("email") || "").trim();
}

function renderHistoryLists(routines, activities) {
  els.routineHistory.innerHTML = renderHistory(routines, "routine");
  els.activityHistory.innerHTML = renderHistory(activities, "activity");
  bindHistoryRows();
}

function resetHistoryDetail(meta = "Selecciona un registro") {
  els.historyDetailTitle.textContent = "Detalle";
  els.historyDetailMeta.textContent = meta;
  els.historyDetailEmpty.style.display = "grid";
  els.historyDetail.style.display = "none";
  els.historyDetail.innerHTML = "";
}

function renderHistory(items, type) {
  // La misma plantilla sirve para rutinas y actividades; cambia el texto segun
  // el tipo de registro.
  if (!items.length) return `<div class="empty-state">Sin registros.</div>`;
  return items
    .map((item) => {
      const date = new Date(item.created_at).toLocaleString("es-ES", {
        day: "2-digit",
        month: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      });
      const title =
        type === "routine"
          ? `${labelObjective(item.objective)} · ${item.level}`
          : `${item.total_minutes} min registrados`;
      const subtitle =
        type === "routine"
          ? `${item.estimated_minutes} min · ${Math.round(item.estimated_calories)} kcal · ${item.environment}`
          : `${Math.round(item.total_calories)} kcal`;
      return `
        <button class="history-row" type="button" data-history-type="${type}" data-history-id="${item.id}">
          <div>
            <strong>${escapeHtml(title)}</strong>
            <span>${escapeHtml(subtitle)}</span>
          </div>
          <span>${date}</span>
        </button>
      `;
    })
    .join("");
}

function bindHistoryRows() {
  document.querySelectorAll("[data-history-type]").forEach((button) => {
    button.addEventListener("click", () => loadHistoryDetail(button.dataset.historyType, button.dataset.historyId));
  });
}

async function loadHistoryDetail(type, id) {
  try {
    const detail = await api(type === "routine" ? `/api/routines/${id}` : `/api/activity/${id}`);
    els.historyDetailEmpty.style.display = "none";
    els.historyDetail.style.display = "grid";
    if (type === "routine") {
      renderRoutineDetail(detail);
    } else {
      renderActivityDetail(detail);
    }
  } catch (error) {
    toast(error.message);
  }
}

function renderRoutineDetail(routine) {
  els.historyDetailTitle.textContent = "Detalle de rutina";
  els.historyDetailMeta.textContent = `${labelObjective(routine.objective)} · ${routine.level} · ${routine.environment}`;
  els.historyDetail.innerHTML = `
    <div class="history-detail-summary">
      <div><strong>${routine.exercises.length}</strong><span>ejercicios</span></div>
      <div><strong>${routine.estimated_minutes}</strong><span>minutos</span></div>
      <div><strong>${Math.round(routine.estimated_calories)}</strong><span>kcal</span></div>
    </div>
    ${routine.exercises.map((item) => renderDetailItem({
      image: item.exercise.image_url,
      name: `${item.order}. ${item.exercise.name}`,
      tags: [item.exercise.target, item.exercise.equipment, `${item.sets} x ${item.reps}`, `${item.rest_seconds}s descanso`],
      value: `${item.minutes} min · ${Math.round(item.calories)} kcal`,
    })).join("")}
  `;
}

function renderActivityDetail(activity) {
  const date = new Date(activity.created_at).toLocaleString("es-ES");
  els.historyDetailTitle.textContent = "Detalle de actividad";
  els.historyDetailMeta.textContent = date;
  els.historyDetail.innerHTML = `
    <div class="history-detail-summary">
      <div><strong>${activity.exercises.length}</strong><span>ejercicios</span></div>
      <div><strong>${activity.total_minutes}</strong><span>minutos</span></div>
      <div><strong>${Math.round(activity.total_calories)}</strong><span>kcal</span></div>
    </div>
    ${activity.exercises.map((item) => renderDetailItem({
      image: item.image_url,
      name: item.name,
      tags: [item.target, item.equipment],
      value: `${item.minutes} min · ${Math.round(item.calories)} kcal`,
    })).join("")}
  `;
}

function renderDetailItem(item) {
  const tags = item.tags.filter(Boolean).map((tag) => `<span class="pill">${escapeHtml(tag)}</span>`).join("");
  return `
    <article class="history-detail-item">
      <img src="${item.image || ""}" alt="${escapeHtml(item.name)}" loading="lazy" />
      <div>
        <h3>${escapeHtml(item.name)}</h3>
        <div class="meta-row">${tags}</div>
      </div>
      <strong>${escapeHtml(item.value)}</strong>
    </article>
  `;
}

function labelObjective(value) {
  const found = state.options?.objectives.find((objective) => objective.value === value);
  return found ? found.label : value;
}

function calories(met, weight, minutes) {
  return (Number(met) * 3.5 * weight * minutes) / 200;
}

function getWeight() {
  return Number(new FormData(els.profileForm).get("weight") || 70);
}

function setBusy(isBusy) {
  const button = els.profileForm.querySelector(".primary-action");
  button.disabled = isBusy;
  button.textContent = isBusy ? "Generando..." : "Generar rutina";
}

function toast(message) {
  els.toast.textContent = message;
  els.toast.classList.add("is-visible");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => els.toast.classList.remove("is-visible"), 2600);
}

function trimText(text, maxLength) {
  if (text.length <= maxLength) return text;
  return `${text.slice(0, maxLength - 1)}...`;
}

function escapeHtml(value) {
  // Las tarjetas se construyen con strings HTML, por eso se escapan datos del
  // dataset y del formulario antes de insertarlos.
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function debounce(callback, delay) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => callback(...args), delay);
  };
}
