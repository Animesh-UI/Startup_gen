"""
🚀 AI Startup Portfolio — Enhanced Edition
New features:
  • Investor CRM  (track investors, pipeline stage, notes)
  • Competitor Analysis  (AI-powered)
  • Team Management  (co-founders / roles)
  • Export Reports  (CSV download)
  • Charts & graphs  (Chart.js via inline JSON)
  • Burn rate / runway calculator
  • MRR / ARR projections
"""

from flask import Flask, request, render_template_string, redirect, Response
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os, random, csv, io
from openai import OpenAI

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///startup.db'
db = SQLAlchemy(app)

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

# ─────────────────────────────────────────
# DATABASE MODELS
# ─────────────────────────────────────────

class Startup(db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    name     = db.Column(db.String(100))
    problem  = db.Column(db.Text)
    industry = db.Column(db.String(50))
    stage    = db.Column(db.String(50))

class Metrics(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    startup_id = db.Column(db.Integer)
    visitors   = db.Column(db.Integer, default=0)
    signups    = db.Column(db.Integer, default=0)
    revenue    = db.Column(db.Integer, default=0)   # cumulative / MRR seed

class Fundraising(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    startup_id = db.Column(db.Integer)
    goal       = db.Column(db.Integer, default=0)
    raised     = db.Column(db.Integer, default=0)
    goal_set   = db.Column(db.Boolean, default=False)

# NEW ──────────────────────────────────────

class Investor(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    startup_id = db.Column(db.Integer)
    name       = db.Column(db.String(100))
    email      = db.Column(db.String(100))
    stage      = db.Column(db.String(50))   # Prospect / Pitched / Term Sheet / Closed / Passed
    amount     = db.Column(db.Integer, default=0)
    notes      = db.Column(db.Text, default='')

class TeamMember(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    startup_id = db.Column(db.Integer)
    name       = db.Column(db.String(100))
    role       = db.Column(db.String(100))
    equity     = db.Column(db.Float, default=0.0)   # percentage

class MonthlyMetric(db.Model):
    """Stores month-by-month snapshots for charting."""
    id         = db.Column(db.Integer, primary_key=True)
    startup_id = db.Column(db.Integer)
    month      = db.Column(db.String(20))  # e.g. "2024-01"
    mrr        = db.Column(db.Integer, default=0)
    visitors   = db.Column(db.Integer, default=0)
    signups    = db.Column(db.Integer, default=0)

class BurnRate(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    startup_id    = db.Column(db.Integer)
    monthly_burn  = db.Column(db.Integer, default=0)
    cash_on_hand  = db.Column(db.Integer, default=0)

# ─────────────────────────────────────────
# AI HELPERS
# ─────────────────────────────────────────

def _ai(prompt: str, max_tokens: int = 500) -> str:
    resp = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens
    )
    return resp.choices[0].message.content


def generate_plan(problem: str) -> str:
    return _ai(f"""Problem: {problem}

Generate ONLY:
1. Target Audience
2. Key Features
3. Launch Roadmap
4. Fundraising Goal
5. Fund Usage Plan

Keep it concise.""")


def generate_competitor_analysis(name: str, problem: str, industry: str) -> str:
    return _ai(f"""Startup: {name}
Industry: {industry}
Problem solved: {problem}

Provide a concise competitive analysis:
1. Top 3 Existing Competitors (name + one-line description)
2. Key Differentiator for {name}
3. SWOT Summary (2 bullet points each)
4. Go-to-market edge

Be specific and actionable.""", max_tokens=600)


# ─────────────────────────────────────────
# HTML TEMPLATES
# ─────────────────────────────────────────

BASE_CSS = """
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', Arial, sans-serif; background: #0a0f1e; color: #e2e8f0; min-height: 100vh; }
  nav { background: #0f172a; padding: 16px 32px; display: flex; align-items: center; gap: 24px; border-bottom: 1px solid #1e3a5f; }
  nav h1 { font-size: 1.3rem; color: #38bdf8; }
  nav a  { color: #94a3b8; text-decoration: none; font-size: 0.9rem; }
  nav a:hover { color: #38bdf8; }
  .container { max-width: 1100px; margin: 0 auto; padding: 32px 20px; }
  .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
  .grid-3 { display: grid; grid-template-columns: repeat(3,1fr); gap: 16px; }
  .card { background: #1e293b; border: 1px solid #1e3a5f; border-radius: 14px; padding: 22px; }
  .card h3 { color: #7dd3fc; margin-bottom: 14px; font-size: 1rem; letter-spacing: .5px; }
  .metric-box { background: #0f172a; border-radius: 10px; padding: 16px; text-align: center; }
  .metric-box .val { font-size: 1.8rem; font-weight: 700; color: #38bdf8; }
  .metric-box .lbl { font-size: 0.75rem; color: #64748b; margin-top: 4px; }
  label { font-size: 0.82rem; color: #94a3b8; display: block; margin: 10px 0 4px; }
  input, textarea, select {
    width: 100%; padding: 9px 12px; border-radius: 8px;
    background: #0f172a; border: 1px solid #334155; color: #e2e8f0;
    font-size: 0.9rem;
  }
  input:focus, textarea:focus, select:focus { outline: none; border-color: #38bdf8; }
  textarea { resize: vertical; min-height: 80px; }
  .btn { display: inline-block; padding: 9px 20px; border-radius: 8px; border: none;
         cursor: pointer; font-size: 0.9rem; font-weight: 600; transition: opacity .2s; }
  .btn:hover { opacity: .85; }
  .btn-primary { background: #38bdf8; color: #0a0f1e; }
  .btn-success { background: #22c55e; color: #0a0f1e; }
  .btn-warn    { background: #f59e0b; color: #0a0f1e; }
  .btn-danger  { background: #ef4444; color: white; }
  .btn-ghost   { background: #334155; color: #e2e8f0; }
  .badge { display: inline-block; padding: 3px 10px; border-radius: 99px; font-size: 0.72rem; font-weight: 600; }
  .badge-prospect   { background:#334155; color:#94a3b8; }
  .badge-pitched    { background:#1e3a5f; color:#7dd3fc; }
  .badge-termsheet  { background:#451a03; color:#fbbf24; }
  .badge-closed     { background:#14532d; color:#4ade80; }
  .badge-passed     { background:#450a0a; color:#f87171; }
  .progress-wrap { background: #0f172a; border-radius: 99px; overflow: hidden; height: 12px; margin: 8px 0; }
  .progress-bar  { background: linear-gradient(90deg,#22c55e,#38bdf8); height: 100%; transition: width .4s; }
  table { width: 100%; border-collapse: collapse; font-size: 0.88rem; }
  th { text-align: left; padding: 10px 12px; background: #0f172a; color: #64748b; font-weight: 600; }
  td { padding: 9px 12px; border-top: 1px solid #1e3a5f; vertical-align: top; }
  tr:hover td { background: #0f172a44; }
  pre { white-space: pre-wrap; font-size: 0.85rem; line-height: 1.6; color: #cbd5e1; }
  .tabs { display: flex; gap: 4px; margin-bottom: 20px; flex-wrap: wrap; }
  .tab-link { padding: 8px 18px; border-radius: 8px; background: #1e293b; color: #94a3b8;
              text-decoration: none; font-size: 0.88rem; border: 1px solid #1e3a5f; }
  .tab-link.active, .tab-link:hover { background: #38bdf8; color: #0a0f1e; border-color: #38bdf8; }
  .runway-ok   { color: #4ade80; }
  .runway-warn { color: #fbbf24; }
  .runway-crit { color: #f87171; }
  canvas { max-width: 100%; }
  .section-title { font-size: 1.1rem; font-weight: 700; color: #e2e8f0; margin-bottom: 16px; }
  .empty { color: #475569; font-size: 0.85rem; padding: 12px 0; }
  a { color: #38bdf8; }
  .startup-card { background:#1e293b; border:1px solid #1e3a5f; border-radius:12px; padding:18px;
                  display:flex; flex-direction:column; gap:8px; }
  .startup-card h3 { color:#e2e8f0; font-size:1rem; }
  .startup-card .meta { font-size:0.78rem; color:#64748b; }
  .startup-card a.view-btn { margin-top:6px; text-align:center; text-decoration:none;
                              background:#334155; color:#7dd3fc; padding:7px 14px;
                              border-radius:8px; font-size:0.82rem; }
  .startup-card a.view-btn:hover { background:#38bdf8; color:#0a0f1e; }
</style>
"""

# ── HOME ──────────────────────────────────

HOME_HTML = BASE_CSS + """
<nav><h1>🚀 Startup OS</h1><a href="/">Portfolio</a></nav>
<div class="container">
  <div class="grid-2" style="align-items:start; gap:30px;">

    <div>
      <div class="section-title">Create New Startup</div>
      <div class="card">
        <form method="POST" action="/create">
          <label>Startup Name</label><input name="name" placeholder="e.g. HealthAI" required>
          <label>Problem Statement</label><textarea name="problem" placeholder="Describe the problem you're solving…" required></textarea>
          <label>Industry</label><input name="industry" placeholder="e.g. HealthTech">
          <label>Stage</label>
          <select name="stage">
            <option>Idea</option><option>MVP</option>
            <option>Pre-Seed</option><option>Seed</option><option>Series A</option>
          </select>
          <label>Monthly Burn Rate (₹)</label><input name="burn" type="number" placeholder="e.g. 50000">
          <label>Cash on Hand (₹)</label><input name="cash" type="number" placeholder="e.g. 500000">
          <br><button class="btn btn-primary" style="margin-top:14px; width:100%;">+ Create Startup</button>
        </form>
      </div>
    </div>

    <div>
      <div class="section-title">Your Portfolio ({{startups|length}})</div>
      {% if startups %}
        {% for s in startups %}
        <div class="startup-card" style="margin-bottom:12px;">
          <h3>{{s.name}}</h3>
          <div class="meta">{{s.industry}} · {{s.stage}}</div>
          <div style="font-size:0.82rem; color:#94a3b8;">{{s.problem[:90]}}{% if s.problem|length > 90 %}…{% endif %}</div>
          <a href="/startup/{{s.id}}" class="view-btn">View Dashboard →</a>
        </div>
        {% endfor %}
      {% else %}
        <div class="empty">No startups yet — create your first one!</div>
      {% endif %}
    </div>

  </div>
</div>
"""

# ── STARTUP DASHBOARD ─────────────────────

STARTUP_HTML = BASE_CSS + """
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<nav>
  <h1>🚀 Startup OS</h1>
  <a href="/">Portfolio</a>
  <a href="/startup/{{s.id}}">{{s.name}}</a>
</nav>

<div class="container">

  <div style="display:flex; align-items:center; gap:16px; margin-bottom:24px;">
    <div>
      <h2 style="font-size:1.6rem; color:#e2e8f0;">{{s.name}}</h2>
      <span style="color:#64748b; font-size:0.85rem;">{{s.industry}} · {{s.stage}}</span>
    </div>
    <div style="margin-left:auto; display:flex; gap:8px; flex-wrap:wrap;">
      <a href="/startup/{{s.id}}/competitor" class="btn btn-warn">🔍 Competitor Analysis</a>
      <a href="/startup/{{s.id}}/export"     class="btn btn-ghost">⬇ Export CSV</a>
      <form method="POST" action="/simulate/{{s.id}}" style="display:inline;">
        <button class="btn btn-success">📈 Simulate Growth</button>
      </form>
    </div>
  </div>

  <!-- TABS -->
  <div class="tabs">
    <a href="#overview"   class="tab-link active" onclick="showTab('overview',this)">Overview</a>
    <a href="#analytics"  class="tab-link" onclick="showTab('analytics',this)">📊 Analytics</a>
    <a href="#fundraising"class="tab-link" onclick="showTab('fundraising',this)">💰 Fundraising</a>
    <a href="#investors"  class="tab-link" onclick="showTab('investors',this)">🤝 Investors</a>
    <a href="#team"       class="tab-link" onclick="showTab('team',this)">👥 Team</a>
    <a href="#burn"       class="tab-link" onclick="showTab('burn',this)">🔥 Burn / Runway</a>
  </div>

  <!-- ─── OVERVIEW ─── -->
  <div id="tab-overview">
    <div class="grid-2" style="margin-bottom:20px;">
      <div class="card">
        <h3>Problem Statement</h3>
        <p style="font-size:0.9rem; color:#cbd5e1; line-height:1.7;">{{s.problem}}</p>
      </div>
      <div class="card">
        <h3>🤖 AI Business Plan</h3>
        <pre>{{ai}}</pre>
      </div>
    </div>

    <div class="grid-3">
      <div class="metric-box card"><div class="val">{{m.visitors}}</div><div class="lbl">Total Visitors</div></div>
      <div class="metric-box card"><div class="val">{{m.signups}}</div><div class="lbl">Signups</div></div>
      <div class="metric-box card"><div class="val">₹{{m.revenue}}</div><div class="lbl">Revenue (MRR seed)</div></div>
    </div>
  </div>

  <!-- ─── ANALYTICS ─── -->
  <div id="tab-analytics" style="display:none;">
    <div class="grid-2">
      <div class="card">
        <h3>MRR Growth</h3>
        <canvas id="mrrChart" height="180"></canvas>
      </div>
      <div class="card">
        <h3>Visitors & Signups</h3>
        <canvas id="vsChart" height="180"></canvas>
      </div>
    </div>
    <div class="card" style="margin-top:20px;">
      <h3>📐 MRR / ARR Projections (next 12 months)</h3>
      <canvas id="projChart" height="130"></canvas>
    </div>
  </div>

  <!-- ─── FUNDRAISING ─── -->
  <div id="tab-fundraising" style="display:none;">
    <div class="grid-2">
      <div class="card">
        <h3>Funding Progress</h3>
        {% if not fund.goal_set %}
          <form method="POST" action="/set_goal/{{s.id}}">
            <label>Set Fundraising Goal (₹)</label>
            <input name="goal" type="number" placeholder="e.g. 5000000" required>
            <button class="btn btn-primary" style="margin-top:10px;">Set Goal</button>
          </form>
        {% else %}
          <div class="grid-2" style="margin-bottom:16px;">
            <div class="metric-box"><div class="val">₹{{fund.goal|int}}</div><div class="lbl">Goal</div></div>
            <div class="metric-box"><div class="val">₹{{fund.raised|int}}</div><div class="lbl">Raised</div></div>
          </div>
          <div class="progress-wrap">
            <div class="progress-bar" style="width:{{ [[(fund.raised/fund.goal*100)|int, 0]|max, 100]|min }}%"></div>
          </div>
          <p style="font-size:0.8rem; color:#64748b; margin-top:6px;">
            {{ (fund.raised/fund.goal*100)|round(1) }}% funded
          </p>
          <form method="POST" action="/fund/{{s.id}}" style="margin-top:14px;">
            <label>Add Investment (₹)</label>
            <input name="amount" type="number" placeholder="e.g. 100000" required>
            <button class="btn btn-success" style="margin-top:8px;">+ Add Funds</button>
          </form>
        {% endif %}
      </div>

      <div class="card">
        <h3>Investor Pipeline Summary</h3>
        <table>
          <tr>
            <th>Stage</th><th>Count</th><th>Total (₹)</th>
          </tr>
          {% for row in inv_summary %}
          <tr>
            <td><span class="badge badge-{{row.stage|lower|replace(' ','')}}">{{row.stage}}</span></td>
            <td>{{row.count}}</td>
            <td>₹{{row.total|int}}</td>
          </tr>
          {% endfor %}
        </table>
      </div>
    </div>
  </div>

  <!-- ─── INVESTORS ─── -->
  <div id="tab-investors" style="display:none;">
    <div class="grid-2" style="align-items:start;">
      <div class="card">
        <h3>Add Investor</h3>
        <form method="POST" action="/investor/add/{{s.id}}">
          <label>Name</label><input name="name" placeholder="Jane Doe" required>
          <label>Email</label><input name="email" type="email" placeholder="jane@vc.com">
          <label>Pipeline Stage</label>
          <select name="stage">
            <option>Prospect</option><option>Pitched</option>
            <option>Term Sheet</option><option>Closed</option><option>Passed</option>
          </select>
          <label>Committed Amount (₹)</label>
          <input name="amount" type="number" placeholder="0">
          <label>Notes</label>
          <textarea name="notes" placeholder="Key discussion points…"></textarea>
          <button class="btn btn-primary" style="margin-top:10px; width:100%;">Add Investor</button>
        </form>
      </div>

      <div class="card">
        <h3>Investor CRM</h3>
        {% if investors %}
        <table>
          <tr><th>Name</th><th>Stage</th><th>Amount</th><th>Notes</th></tr>
          {% for inv in investors %}
          <tr>
            <td>{{inv.name}}<br><span style="font-size:0.75rem;color:#64748b;">{{inv.email}}</span></td>
            <td><span class="badge badge-{{inv.stage|lower|replace(' ','')}}">{{inv.stage}}</span></td>
            <td>₹{{inv.amount|int}}</td>
            <td style="font-size:0.78rem; color:#94a3b8;">{{inv.notes[:60]}}{% if inv.notes|length > 60 %}…{% endif %}</td>
          </tr>
          {% endfor %}
        </table>
        {% else %}
          <div class="empty">No investors tracked yet.</div>
        {% endif %}
      </div>
    </div>
  </div>

  <!-- ─── TEAM ─── -->
  <div id="tab-team" style="display:none;">
    <div class="grid-2" style="align-items:start;">
      <div class="card">
        <h3>Add Team Member</h3>
        <form method="POST" action="/team/add/{{s.id}}">
          <label>Full Name</label><input name="name" placeholder="Arjun Sharma" required>
          <label>Role</label><input name="role" placeholder="e.g. CTO / Head of Marketing">
          <label>Equity (%)</label>
          <input name="equity" type="number" step="0.01" placeholder="e.g. 10.5">
          <button class="btn btn-primary" style="margin-top:10px; width:100%;">Add Member</button>
        </form>
      </div>

      <div class="card">
        <h3>Team Roster</h3>
        {% if team %}
        <table>
          <tr><th>Name</th><th>Role</th><th>Equity</th></tr>
          {% for t in team %}
          <tr>
            <td>{{t.name}}</td>
            <td style="color:#94a3b8;">{{t.role}}</td>
            <td>{{t.equity}}%</td>
          </tr>
          {% endfor %}
        </table>
        <div style="margin-top:12px;">
          <div class="progress-wrap">
            <div class="progress-bar" style="width:{{total_equity}}%; background:linear-gradient(90deg,#a855f7,#38bdf8);"></div>
          </div>
          <p style="font-size:0.78rem; color:#64748b; margin-top:4px;">
            {{total_equity}}% equity allocated · {{100 - total_equity|round(2)}}% available
          </p>
        </div>
        {% else %}
          <div class="empty">No team members added yet.</div>
        {% endif %}
      </div>
    </div>
  </div>

  <!-- ─── BURN / RUNWAY ─── -->
  <div id="tab-burn" style="display:none;">
    <div class="grid-2" style="align-items:start;">
      <div class="card">
        <h3>Update Burn Rate</h3>
        <form method="POST" action="/burn/update/{{s.id}}">
          <label>Monthly Burn Rate (₹)</label>
          <input name="burn" type="number" value="{{burn.monthly_burn}}" placeholder="e.g. 75000" required>
          <label>Cash on Hand (₹)</label>
          <input name="cash" type="number" value="{{burn.cash_on_hand}}" placeholder="e.g. 1000000" required>
          <button class="btn btn-warn" style="margin-top:10px; width:100%;">Update</button>
        </form>
      </div>

      <div class="card">
        <h3>Runway Analysis</h3>
        {% if burn.monthly_burn > 0 %}
          {% set runway = (burn.cash_on_hand / burn.monthly_burn)|round(1) %}
          <div style="text-align:center; padding:20px 0;">
            <div style="font-size:3rem; font-weight:800;
              {% if runway >= 12 %}color:#4ade80;
              {% elif runway >= 6 %}color:#fbbf24;
              {% else %}color:#f87171;{% endif %}">
              {{runway}} <span style="font-size:1.2rem;">months</span>
            </div>
            <div style="color:#64748b; margin-top:8px;">Estimated Runway</div>
          </div>

          <div class="grid-2" style="margin-top:10px;">
            <div class="metric-box"><div class="val" style="font-size:1.2rem;">₹{{burn.monthly_burn|int}}</div><div class="lbl">Monthly Burn</div></div>
            <div class="metric-box"><div class="val" style="font-size:1.2rem;">₹{{burn.cash_on_hand|int}}</div><div class="lbl">Cash on Hand</div></div>
          </div>

          {% if runway < 6 %}
            <div style="margin-top:14px; background:#450a0a; border:1px solid #f87171; border-radius:10px; padding:12px; font-size:0.85rem; color:#fca5a5;">
              ⚠️ <strong>Critical:</strong> Less than 6 months runway. Prioritise fundraising immediately.
            </div>
          {% elif runway < 12 %}
            <div style="margin-top:14px; background:#451a03; border:1px solid #fbbf24; border-radius:10px; padding:12px; font-size:0.85rem; color:#fde68a;">
              ⚡ <strong>Warning:</strong> Under 12 months runway. Start fundraising conversations now.
            </div>
          {% else %}
            <div style="margin-top:14px; background:#14532d; border:1px solid #22c55e; border-radius:10px; padding:12px; font-size:0.85rem; color:#bbf7d0;">
              ✅ <strong>Healthy:</strong> Strong runway. Focus on growth.
            </div>
          {% endif %}

        {% else %}
          <div class="empty">Enter burn rate to calculate runway.</div>
        {% endif %}
      </div>
    </div>
  </div>

</div><!-- /container -->

<script>
// ── TABS ──────────────────────────────────
function showTab(name, el) {
  document.querySelectorAll('[id^="tab-"]').forEach(t => t.style.display = 'none');
  document.getElementById('tab-' + name).style.display = 'block';
  document.querySelectorAll('.tab-link').forEach(a => a.classList.remove('active'));
  el.classList.add('active');
  if (name === 'analytics') renderCharts();
}

// ── CHART DATA (injected server-side) ────
const months   = {{ months_json|safe }};
const mrrData  = {{ mrr_json|safe }};
const visData  = {{ vis_json|safe }};
const sigData  = {{ sig_json|safe }};
const currMRR  = {{ m.revenue }};

// ── CHART.JS ─────────────────────────────
let chartsRendered = false;
function renderCharts() {
  if (chartsRendered) return;
  chartsRendered = true;

  const baseOpts = {
    responsive: true,
    plugins: { legend: { labels: { color: '#94a3b8' } } },
    scales: {
      x: { ticks: { color: '#64748b' }, grid: { color: '#1e293b' } },
      y: { ticks: { color: '#64748b' }, grid: { color: '#1e293b' } }
    }
  };

  // MRR chart
  new Chart(document.getElementById('mrrChart'), {
    type: 'line',
    data: {
      labels: months,
      datasets: [{ label: 'MRR (₹)', data: mrrData,
        borderColor: '#38bdf8', backgroundColor: 'rgba(56,189,248,0.15)',
        fill: true, tension: 0.4 }]
    },
    options: baseOpts
  });

  // Visitors & Signups
  new Chart(document.getElementById('vsChart'), {
    type: 'bar',
    data: {
      labels: months,
      datasets: [
        { label: 'Visitors', data: visData, backgroundColor: 'rgba(56,189,248,0.7)' },
        { label: 'Signups',  data: sigData, backgroundColor: 'rgba(34,197,94,0.7)' }
      ]
    },
    options: { ...baseOpts, scales: { ...baseOpts.scales, x: { ...baseOpts.scales.x, stacked: false } } }
  });

  // ARR projections (12-month compound 10% growth assumption)
  const projLabels = [], projMRR = [], projARR = [];
  let base = currMRR;
  for (let i = 1; i <= 12; i++) {
    base = Math.round(base * 1.10);
    const d = new Date(); d.setMonth(d.getMonth() + i);
    projLabels.push(d.toLocaleString('default',{month:'short', year:'2-digit'}));
    projMRR.push(base);
    projARR.push(base * 12);
  }
  new Chart(document.getElementById('projChart'), {
    type: 'line',
    data: {
      labels: projLabels,
      datasets: [
        { label: 'Projected MRR (₹)', data: projMRR,
          borderColor: '#a78bfa', backgroundColor: 'rgba(167,139,250,0.1)', fill: true, tension: 0.4 },
        { label: 'Projected ARR (₹)', data: projARR,
          borderColor: '#f59e0b', backgroundColor: 'rgba(245,158,11,0.1)', fill: true, tension: 0.4 }
      ]
    },
    options: { ...baseOpts }
  });
}
</script>
"""

# ── COMPETITOR ANALYSIS ───────────────────

COMPETITOR_HTML = BASE_CSS + """
<nav><h1>🚀 Startup OS</h1><a href="/">Portfolio</a>
<a href="/startup/{{s.id}}">{{s.name}}</a></nav>
<div class="container">
  <h2 style="margin-bottom:20px;">🔍 Competitor Analysis — {{s.name}}</h2>
  <div class="card"><pre>{{analysis}}</pre></div>
  <a href="/startup/{{s.id}}" class="btn btn-ghost" style="margin-top:16px; display:inline-block;">← Back to Dashboard</a>
</div>
"""

# ─────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────

@app.route('/')
def home():
    startups = Startup.query.all()
    return render_template_string(HOME_HTML, startups=startups)


@app.route('/create', methods=['POST'])
def create():
    s = Startup(
        name=request.form['name'],
        problem=request.form['problem'],
        industry=request.form['industry'],
        stage=request.form['stage']
    )
    db.session.add(s)
    db.session.flush()   # get s.id

    burn = int(request.form.get('burn') or 50000)
    cash = int(request.form.get('cash') or 500000)

    db.session.add(Metrics(startup_id=s.id, visitors=10, signups=2, revenue=5000))
    db.session.add(Fundraising(startup_id=s.id, goal=1000000, raised=0))
    db.session.add(BurnRate(startup_id=s.id, monthly_burn=burn, cash_on_hand=cash))

    # seed 3 months of history
    import datetime
    for i in range(3, 0, -1):
        dt = datetime.date.today().replace(day=1)
        # go back i months
        month_dt = (dt.replace(day=1) - datetime.timedelta(days=1))
        for _ in range(i - 1):
            month_dt = (month_dt.replace(day=1) - datetime.timedelta(days=1))
        label = month_dt.strftime('%Y-%m')
        db.session.add(MonthlyMetric(
            startup_id=s.id,
            month=label,
            mrr=random.randint(2000, 8000),
            visitors=random.randint(50, 300),
            signups=random.randint(5, 40)
        ))

    db.session.commit()
    return redirect('/')


@app.route('/startup/<int:id>')
def startup(id):
    s   = Startup.query.get_or_404(id)
    m   = Metrics.query.filter_by(startup_id=id).first()
    f   = Fundraising.query.filter_by(startup_id=id).first()
    burn= BurnRate.query.filter_by(startup_id=id).first()
    investors = Investor.query.filter_by(startup_id=id).all()
    team      = TeamMember.query.filter_by(startup_id=id).all()
    history   = MonthlyMetric.query.filter_by(startup_id=id).order_by(MonthlyMetric.month).all()

    total_equity = round(sum(t.equity for t in team), 2)

    # investor pipeline summary
    from collections import defaultdict
    inv_map = defaultdict(lambda: {'count': 0, 'total': 0})
    for inv in investors:
        inv_map[inv.stage]['count'] += 1
        inv_map[inv.stage]['total'] += inv.amount
    inv_summary = [{'stage': k, **v} for k, v in inv_map.items()]

    # chart data
    import json
    months_json = json.dumps([h.month for h in history])
    mrr_json    = json.dumps([h.mrr for h in history])
    vis_json    = json.dumps([h.visitors for h in history])
    sig_json    = json.dumps([h.signups for h in history])

    ai = generate_plan(s.problem)

    return render_template_string(
        STARTUP_HTML,
        s=s, m=m, fund=f, burn=burn,
        investors=investors, team=team,
        total_equity=total_equity,
        inv_summary=inv_summary,
        months_json=months_json,
        mrr_json=mrr_json,
        vis_json=vis_json,
        sig_json=sig_json,
        ai=ai
    )


@app.route('/startup/<int:id>/competitor')
def competitor(id):
    s = Startup.query.get_or_404(id)
    analysis = generate_competitor_analysis(s.name, s.problem, s.industry)
    return render_template_string(COMPETITOR_HTML, s=s, analysis=analysis)


@app.route('/simulate/<int:id>', methods=['POST'])
def simulate(id):
    import datetime
    m = Metrics.query.filter_by(startup_id=id).first()
    m.visitors += random.randint(20, 150)
    m.signups  += random.randint(2,  30)
    m.revenue  += random.randint(500, 5000)

    # also record a monthly snapshot for this month
    label = datetime.date.today().strftime('%Y-%m')
    snap  = MonthlyMetric.query.filter_by(startup_id=id, month=label).first()
    if snap:
        snap.mrr      = m.revenue
        snap.visitors = m.visitors
        snap.signups  = m.signups
    else:
        db.session.add(MonthlyMetric(
            startup_id=id, month=label,
            mrr=m.revenue, visitors=m.visitors, signups=m.signups
        ))

    db.session.commit()
    return redirect(f'/startup/{id}')


@app.route('/set_goal/<int:id>', methods=['POST'])
def set_goal(id):
    f = Fundraising.query.filter_by(startup_id=id).first()
    f.goal     = int(request.form['goal'])
    f.goal_set = True
    db.session.commit()
    return redirect(f'/startup/{id}')


@app.route('/fund/<int:id>', methods=['POST'])
def fund(id):
    f = Fundraising.query.filter_by(startup_id=id).first()
    f.raised += int(request.form['amount'])
    if f.raised > f.goal:
        f.goal = int(f.raised * 1.5)
    db.session.commit()
    return redirect(f'/startup/{id}')


@app.route('/investor/add/<int:id>', methods=['POST'])
def add_investor(id):
    db.session.add(Investor(
        startup_id=id,
        name  =request.form['name'],
        email =request.form.get('email', ''),
        stage =request.form['stage'],
        amount=int(request.form.get('amount') or 0),
        notes =request.form.get('notes', '')
    ))
    db.session.commit()
    return redirect(f'/startup/{id}')


@app.route('/team/add/<int:id>', methods=['POST'])
def add_team(id):
    db.session.add(TeamMember(
        startup_id=id,
        name  =request.form['name'],
        role  =request.form.get('role', ''),
        equity=float(request.form.get('equity') or 0)
    ))
    db.session.commit()
    return redirect(f'/startup/{id}')


@app.route('/burn/update/<int:id>', methods=['POST'])
def update_burn(id):
    b = BurnRate.query.filter_by(startup_id=id).first()
    b.monthly_burn = int(request.form['burn'])
    b.cash_on_hand = int(request.form['cash'])
    db.session.commit()
    return redirect(f'/startup/{id}')


@app.route('/startup/<int:id>/export')
def export_csv(id):
    s         = Startup.query.get_or_404(id)
    m         = Metrics.query.filter_by(startup_id=id).first()
    f         = Fundraising.query.filter_by(startup_id=id).first()
    burn      = BurnRate.query.filter_by(startup_id=id).first()
    investors = Investor.query.filter_by(startup_id=id).all()
    team      = TeamMember.query.filter_by(startup_id=id).all()
    history   = MonthlyMetric.query.filter_by(startup_id=id).order_by(MonthlyMetric.month).all()

    buf = io.StringIO()
    w   = csv.writer(buf)

    w.writerow(['=== STARTUP INFO ==='])
    w.writerow(['Name', 'Industry', 'Stage', 'Problem'])
    w.writerow([s.name, s.industry, s.stage, s.problem])

    w.writerow([])
    w.writerow(['=== METRICS ==='])
    w.writerow(['Visitors', 'Signups', 'Revenue (MRR)'])
    w.writerow([m.visitors, m.signups, m.revenue])

    w.writerow([])
    w.writerow(['=== FUNDRAISING ==='])
    w.writerow(['Goal (₹)', 'Raised (₹)'])
    w.writerow([f.goal, f.raised])

    w.writerow([])
    w.writerow(['=== BURN RATE ==='])
    w.writerow(['Monthly Burn (₹)', 'Cash on Hand (₹)', 'Runway (months)'])
    runway = round(burn.cash_on_hand / burn.monthly_burn, 1) if burn.monthly_burn else 'N/A'
    w.writerow([burn.monthly_burn, burn.cash_on_hand, runway])

    w.writerow([])
    w.writerow(['=== INVESTOR CRM ==='])
    w.writerow(['Name', 'Email', 'Stage', 'Amount (₹)', 'Notes'])
    for inv in investors:
        w.writerow([inv.name, inv.email, inv.stage, inv.amount, inv.notes])

    w.writerow([])
    w.writerow(['=== TEAM ==='])
    w.writerow(['Name', 'Role', 'Equity (%)'])
    for t in team:
        w.writerow([t.name, t.role, t.equity])

    w.writerow([])
    w.writerow(['=== MONTHLY HISTORY ==='])
    w.writerow(['Month', 'MRR (₹)', 'Visitors', 'Signups'])
    for h in history:
        w.writerow([h.month, h.mrr, h.visitors, h.signups])

    return Response(
        buf.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={s.name.replace(" ","_")}_report.csv'}
    )


# ─────────────────────────────────────────
# INIT
# ─────────────────────────────────────────
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
