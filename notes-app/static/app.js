/* 记事 APP 原型前端逻辑 */
(function () {
  "use strict";

  const $ = (sel) => document.querySelector(sel);

  const state = {
    notes: [],
    currentId: null,
    filters: { q: "", category: "", tag: "" },
    saveTimer: null,
    reminded: new Set(),
  };

  // ----------------------------- API -----------------------------

  async function api(method, url, body) {
    const opt = { method, headers: {} };
    if (body !== undefined) {
      opt.headers["Content-Type"] = "application/json";
      opt.body = JSON.stringify(body);
    }
    const resp = await fetch(url, opt);
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.error || `请求失败 ${resp.status}`);
    }
    const ct = resp.headers.get("Content-Type") || "";
    return ct.includes("application/json") ? resp.json() : resp.text();
  }

  // ----------------------------- 工具 -----------------------------

  function toast(msg) {
    const el = $("#toast");
    el.textContent = msg;
    el.hidden = false;
    clearTimeout(toast._t);
    toast._t = setTimeout(() => (el.hidden = true), 1800);
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
  }

  function textFromHtml(htmlStr) {
    const div = document.createElement("div");
    div.innerHTML = htmlStr || "";
    return (div.textContent || "").trim();
  }

  function fmtTime(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    if (isNaN(d)) return iso;
    const p = (n) => String(n).padStart(2, "0");
    return `${d.getMonth() + 1}/${d.getDate()} ${p(d.getHours())}:${p(d.getMinutes())}`;
  }

  function toLocalInput(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    if (isNaN(d)) return "";
    const p = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`;
  }

  // ----------------------------- 数据加载 -----------------------------

  async function loadNotes() {
    const params = new URLSearchParams();
    if (state.filters.q) params.set("q", state.filters.q);
    if (state.filters.category) params.set("category", state.filters.category);
    if (state.filters.tag) params.set("tag", state.filters.tag);
    const data = await api("GET", `/api/notes?${params}`);
    state.notes = data.notes || [];
    renderList();
    loadMeta();
  }

  async function loadMeta() {
    const meta = await api("GET", "/api/meta");
    renderSidebarMeta(meta);
  }

  // ----------------------------- 渲染 -----------------------------

  function renderList() {
    const list = $("#note-list");
    $("#list-count").textContent = `共 ${state.notes.length} 条笔记`;
    list.innerHTML = "";

    if (!state.notes.length) {
      list.innerHTML = `<div class="note-card" style="cursor:default;color:var(--muted)">暂无笔记，点击「新建笔记」开始记录</div>`;
      return;
    }

    state.notes.forEach((n) => {
      const done = (n.todos || []).filter((t) => t.done).length;
      const total = (n.todos || []).length;
      const remind = n.reminder_at && new Date(n.reminder_at) > new Date()
        ? `<span class="nc-remind">⏰ ${fmtTime(n.reminder_at)}</span>` : "";
      const todo = total ? `<span class="nc-todo">☑ ${done}/${total}</span>` : "";
      const tags = (n.tags || []).map((t) => `<span class="nc-tag">#${escapeHtml(t)}</span>`).join("");
      const card = document.createElement("div");
      card.className = "note-card" + (n.id === state.currentId ? " active" : "");
      card.innerHTML = `
        <div class="nc-title ${n.title ? "" : "empty"}">${escapeHtml(n.title || "无标题")}</div>
        <div class="nc-summary">${escapeHtml(textFromHtml(n.content)) || "（无正文）"}</div>
        <div class="nc-meta">
          <span class="nc-cat">${escapeHtml(n.category)}</span>
          ${tags}${todo}${remind}
          <span>${fmtTime(n.updated_at)}</span>
        </div>`;
      card.addEventListener("click", () => selectNote(n.id));
      list.appendChild(card);
    });
  }

  function renderSidebarMeta(meta) {
    const catList = $("#category-list");
    const cats = ["", ...meta.categories];
    catList.innerHTML = cats.map((c) => {
      const label = c || "全部";
      const count = c ? state.notes.filter((n) => n.category === c).length : state.notes.length;
      const active = state.filters.category === c ? " active" : "";
      return `<li class="${active}" data-cat="${escapeHtml(c)}"><span>${label}</span><span class="count">${count}</span></li>`;
    }).join("");

    catList.querySelectorAll("li").forEach((li) => {
      li.addEventListener("click", () => {
        state.filters.category = li.dataset.cat;
        loadNotes();
      });
    });

    const cloud = $("#tag-cloud");
    cloud.innerHTML = "";
    meta.tags.forEach((t) => {
      const el = document.createElement("span");
      el.className = "tag" + (state.filters.tag === t ? " active" : "");
      el.textContent = `#${t}`;
      el.addEventListener("click", () => {
        state.filters.tag = state.filters.tag === t ? "" : t;
        loadNotes();
      });
      cloud.appendChild(el);
    });

    const datalist = $("#category-datalist");
    datalist.innerHTML = meta.categories.map((c) => `<option value="${escapeHtml(c)}">`).join("");
  }

  function renderTodos() {
    const box = $("#todo-list");
    box.innerHTML = "";
    const note = currentDraft();
    (note.todos || []).forEach((t) => {
      const li = document.createElement("li");
      li.className = "todo-item" + (t.done ? " done" : "");
      li.innerHTML = `
        <input type="checkbox" ${t.done ? "checked" : ""} />
        <span class="todo-text">${escapeHtml(t.text)}</span>
        ${t.reminder ? `<span class="todo-reminder">⏰ ${fmtTime(t.reminder)}</span>` : ""}
        <button class="todo-del" title="删除">✕</button>`;
      li.querySelector("input").addEventListener("change", (e) => {
        t.done = e.target.checked;
        renderTodos();
        scheduleSave();
      });
      li.querySelector(".todo-text").addEventListener("dblclick", () => {
        const nv = prompt("编辑待办", t.text);
        if (nv !== null) { t.text = nv.trim() || t.text; renderTodos(); scheduleSave(); }
      });
      li.querySelector(".todo-del").addEventListener("click", () => {
        note.todos = note.todos.filter((x) => x.id !== t.id);
        renderTodos();
        scheduleSave();
      });
      box.appendChild(li);
    });
  }

  // ----------------------------- 表单组装 -----------------------------

  function currentDraft() {
    return state._draft || {};
  }

  function collectForm() {
    const clean = (v) => {
      v = (v || "").trim();
      return v === "undefined" || v === "null" ? "" : v;
    };
    const tagStr = clean($("#note-tags").value);
    const tags = tagStr ? tagStr.split(/[,，]/).map((s) => s.trim()).filter(Boolean) : [];
    return {
      title: clean($("#note-title").value),
      content: $("#note-content").innerHTML,
      category: clean($("#note-category").value) || "未分类",
      tags,
      todos: currentDraft().todos || [],
      reminder_at: $("#note-reminder").value || null,
    };
  }

  function fillForm(note) {
    note = note || {};
    state._draft = {
      title: note.title || "",
      content: note.content || "",
      category: note.category || "",
      tags: note.tags || [],
      todos: note.todos || [],
      reminder_at: note.reminder_at || null,
    };
    $("#note-title").value = note.title || "";
    $("#note-content").innerHTML = note.content || "";
    $("#note-category").value = note.category || "";
    $("#note-tags").value = (note.tags || []).join(", ");
    $("#note-reminder").value = toLocalInput(note.reminder_at || null);
    renderTodos();
  }

  // ----------------------------- 操作 -----------------------------

  async function selectNote(id) {
    if (state.currentId !== null) await persistSilent();
    const n = await api("GET", `/api/notes/${id}`);
    state.currentId = id;
    fillForm(n);
    renderList();
  }

  function newNote() {
    state.currentId = null;
    fillForm({ todos: [] });
    $("#note-title").focus();
  }

  function scheduleSave() {
    clearTimeout(state.saveTimer);
    state.saveTimer = setTimeout(() => persist(true), 1500);
  }

  async function persistSilent() {
    try { await persist(false); } catch (e) { /* 静默 */ }
  }

  async function persist(showToast) {
    const data = collectForm();
    if (!data.title && !textFromHtml(data.content) && !data.todos.length) {
      if (showToast) toast("内容为空，未保存");
      return;
    }
    if (state.currentId === null) {
      const created = await api("POST", "/api/notes", data);
      state.currentId = created.id;
    } else {
      await api("PUT", `/api/notes/${state.currentId}`, data);
    }
    state._draft.todos = data.todos;
    await loadNotes();
    if (showToast) toast("已保存");
    setSyncStatus(true);
  }

  async function deleteCurrent() {
    if (state.currentId === null) return;
    if (!confirm("确定删除这条笔记？")) return;
    await api("DELETE", `/api/notes/${state.currentId}`);
    state.currentId = null;
    fillForm({ todos: [] });
    await loadNotes();
    toast("已删除");
  }

  function exportFile(format) {
    if (state.currentId === null) { toast("请先保存笔记"); return; }
    persistSilent().then(() => {
      window.location.href = `/api/notes/${state.currentId}/export?format=${format}`;
    });
  }

  // ----------------------------- 图片 -----------------------------

  function insertImage(file) {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = async () => {
      try {
        const data = await api("POST", "/api/images", { data_url: reader.result });
        document.execCommand("insertHTML", false, `<img src="${data.url}" alt="图片" />`);
        scheduleSave();
      } catch (e) {
        toast("图片上传失败：" + e.message);
      }
    };
    reader.readAsDataURL(file);
  }

  // ----------------------------- 提醒 -----------------------------

  function checkReminders() {
    const now = new Date();
    state.notes.forEach((n) => {
      const hits = [];
      if (n.reminder_at) hits.push({ at: n.reminder_at, label: n.title || "无标题" });
      (n.todos || []).forEach((t) => {
        if (t.reminder && !t.done) hits.push({ at: t.reminder, label: "待办：" + t.text });
      });
      hits.forEach((h) => {
        const key = `${n.id}-${h.at}-${h.label}`;
        if (new Date(h.at) <= now && !state.reminded.has(key)) {
          state.reminded.add(key);
          toast(`⏰ 提醒：${h.label}`);
          if (Notification.permission === "granted") {
            new Notification("记事提醒", { body: h.label });
          }
        }
      });
    });
  }

  // ----------------------------- 状态 -----------------------------

  function setSyncStatus(online) {
    const el = $("#sync-status");
    el.textContent = online ? "● 已同步到服务端" : "● 连接中…";
    el.style.color = online ? "#34a853" : "var(--muted)";
  }

  // ----------------------------- 事件绑定 -----------------------------

  function bindEvents() {
    $("#btn-new").addEventListener("click", newNote);
    $("#btn-save").addEventListener("click", () => persist(true));
    $("#btn-delete").addEventListener("click", deleteCurrent);
    $("#btn-export-md").addEventListener("click", () => exportFile("md"));
    $("#btn-export-txt").addEventListener("click", () => exportFile("txt"));

    let searchTimer;
    $("#search-input").addEventListener("input", (e) => {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(() => {
        state.filters.q = e.target.value.trim();
        loadNotes();
      }, 300);
    });

    // 富文本工具栏
    document.querySelectorAll(".toolbar [data-cmd]").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        document.execCommand(btn.dataset.cmd, false, null);
        $("#note-content").focus();
      });
    });

    $("#btn-insert-image").addEventListener("click", () => $("#file-image").click());
    $("#file-image").addEventListener("change", (e) => insertImage(e.target.files[0]));

    // 正文/标题变更 → 防抖保存
    ["#note-title", "#note-category", "#note-tags", "#note-reminder"].forEach((sel) => {
      $(sel).addEventListener("input", scheduleSave);
    });
    $("#note-content").addEventListener("input", scheduleSave);

    $("#btn-add-todo").addEventListener("click", () => {
      const text = prompt("待办内容");
      if (!text || !text.trim()) return;
      const note = currentDraft();
      note.todos = note.todos || [];
      note.todos.push({
        id: Date.now().toString(36),
        text: text.trim(),
        done: false,
        reminder: null,
      });
      renderTodos();
      scheduleSave();
    });

    // 定时同步与提醒检查
    setInterval(() => { persistSilent().then(loadNotes); }, 15000);
    setInterval(checkReminders, 30000);

    if ("Notification" in window && Notification.permission === "default") {
      Notification.requestPermission();
    }
  }

  // ----------------------------- 启动 -----------------------------

  async function init() {
    bindEvents();
    await loadNotes();
    if (state.notes.length) {
      await selectNote(state.notes[0].id);
    } else {
      newNote();
    }
    setSyncStatus(true);
  }

  init().catch((e) => {
    console.error(e);
    toast("初始化失败：" + e.message);
  });
})();
