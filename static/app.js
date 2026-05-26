/* LLM SEO Analyzer — client-side logic */

const form = document.getElementById("analyze-form");
const urlInput = document.getElementById("url-input");
const submitBtn = document.getElementById("submit-btn");
const loadingEl = document.getElementById("loading");
const errorEl = document.getElementById("error");
const reportEl = document.getElementById("report");
const scoreCircle = document.getElementById("score-circle");
const scoreNumber = document.getElementById("score-number");
const gradeBadge = document.getElementById("grade-badge");
const analyzedUrl = document.getElementById("analyzed-url");
const checksList = document.getElementById("checks-list");

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const url = urlInput.value.trim();
  if (!url) return;

  // Reset UI
  reportEl.classList.add("hidden");
  errorEl.classList.add("hidden");
  loadingEl.classList.remove("hidden");
  submitBtn.disabled = true;

  try {
    const res = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || "Analysis failed");
    }

    const report = await res.json();
    renderReport(report);
  } catch (err) {
    errorEl.textContent = `Error: ${err.message}`;
    errorEl.classList.remove("hidden");
  } finally {
    loadingEl.classList.add("hidden");
    submitBtn.disabled = false;
  }
});

function renderReport(report) {
  // Score
  scoreNumber.textContent = report.score;
  scoreCircle.style.borderColor = report.grade.color;
  scoreNumber.style.color = report.grade.color;

  // Grade badge
  gradeBadge.textContent = `${report.grade.letter} — ${report.grade.label}`;
  gradeBadge.style.background = report.grade.color;

  // URL
  analyzedUrl.textContent = report.resolved_url || report.url;

  // Checks
  checksList.innerHTML = "";
  for (const check of report.checks) {
    checksList.appendChild(createCheckCard(check));
  }

  reportEl.classList.remove("hidden");
}

function createCheckCard(check) {
  const card = document.createElement("div");
  card.className = "check-card";

  const header = document.createElement("div");
  header.className = "check-header";
  header.innerHTML = `
    <span class="check-status-dot ${check.status}"></span>
    <span class="check-name">${esc(check.name)}</span>
    <span class="check-score">${check.score}/${check.max_score}</span>
    <span class="check-chevron">▶</span>
  `;

  header.addEventListener("click", () => card.classList.toggle("open"));

  const body = document.createElement("div");
  body.className = "check-body";

  if (check.findings.length) {
    body.innerHTML += `<h4>Findings</h4>`;
    const ul = document.createElement("ul");
    ul.className = "findings-list";
    for (const f of check.findings) {
      const li = document.createElement("li");
      li.textContent = f;
      ul.appendChild(li);
    }
    body.appendChild(ul);
  }

  if (check.actions.length) {
    body.innerHTML += `<h4>Recommended Actions</h4>`;
    const ul = document.createElement("ul");
    ul.className = "actions-list";
    for (const a of check.actions) {
      const li = document.createElement("li");
      li.textContent = a;
      ul.appendChild(li);
    }
    body.appendChild(ul);
  }

  if (!check.findings.length && !check.actions.length) {
    body.innerHTML += `<p style="color:var(--text-muted)">No issues found.</p>`;
  }

  card.appendChild(header);
  card.appendChild(body);
  return card;
}

function esc(str) {
  const d = document.createElement("div");
  d.textContent = str;
  return d.innerHTML;
}
