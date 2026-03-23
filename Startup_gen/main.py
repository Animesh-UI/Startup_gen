# 🚀 AI Startup Portfolio + Fundraising + Analytics (Advanced)

from flask import Flask, request, render_template_string, redirect
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os, random
from openai import OpenAI

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///startup.db'
db = SQLAlchemy(app)

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

# ---------------- DATABASE ----------------
class Startup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    problem = db.Column(db.Text)
    industry = db.Column(db.String(50))
    stage = db.Column(db.String(50))

class Metrics(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    startup_id = db.Column(db.Integer)
    visitors = db.Column(db.Integer, default=0)
    signups = db.Column(db.Integer, default=0)
    revenue = db.Column(db.Integer, default=0)

class Fundraising(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    startup_id = db.Column(db.Integer)
    goal = db.Column(db.Integer, default=0)
    raised = db.Column(db.Integer, default=0)
    goal_set = db.Column(db.Boolean, default=False)  # track if user set goal

# ---------------- AI ----------------
def generate_ai(problem):
    prompt = f"""
    Problem: {problem}

    Generate ONLY:
    1. Target Audience
    2. Key Features
    3. Launch Roadmap
    4. Fundraising Goal
    5. Fund Usage Plan

    Keep it concise.
    """

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=400
    )

    return response.choices[0].message.content

# ---------------- HTML ----------------
HOME_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Startup Dashboard</title>
<style>
body { font-family: Arial; background: #0f172a; color: white; padding: 30px; }
.card { background: #1e293b; padding: 20px; border-radius: 12px; margin-top: 20px; }
input, textarea { width: 100%; padding: 10px; margin: 5px 0; border-radius: 8px; }
button { background: #38bdf8; padding: 10px; border-radius: 8px; }
a { color: #7dd3fc; }
</style>
</head>
<body>
<h1>🚀 Startup Portfolio</h1>

<div class="card">
<h2>Create Startup</h2>
<form method='POST' action='/create'>
<input name='name' placeholder='Startup Name'>
<textarea name='problem' placeholder='Problem'></textarea>
<input name='industry' placeholder='Industry'>
<input name='stage' placeholder='Stage'>
<button>Create</button>
</form>
</div>

<div class="card">
<h2>Your Startups</h2>
{% for s in startups %}
<div>
<a href='/startup/{{s.id}}'>{{s.name}}</a>
</div>
{% endfor %}
</div>
</body>
</html>
"""

STARTUP_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Startup</title>
<style>
body { font-family: Arial; background: #020617; color: white; padding: 30px; }
.card { background: #1e293b; padding: 20px; border-radius: 12px; margin-top: 20px; }
.metric { display: inline-block; width: 30%; background: #334155; padding: 15px; border-radius: 10px; margin: 5px; text-align: center; }
.progress { background: #334155; border-radius: 10px; overflow: hidden; }
.bar { background: #22c55e; height: 20px; }
button { padding: 10px; border-radius: 8px; }
pre { white-space: pre-wrap; }
</style>
</head>
<body>

<h1>{{startup.name}}</h1>

<div class="card">
<h3>Problem</h3>
<p>{{startup.problem}}</p>
</div>

<div class="card">
<h3>AI Plan</h3>
<pre>{{ai}}</pre>
</div>

<div class="card">
<h3>📊 Metrics</h3>
<div class="metric">Visitors<br>{{metrics.visitors}}</div>
<div class="metric">Signups<br>{{metrics.signups}}</div>
<div class="metric">Revenue<br>₹{{metrics.revenue}}</div>
</div>

<div class="card">
<h3>💰 Fundraising</h3>

{% if not fund.goal_set %}
<form method='POST' action='/set_goal/{{startup.id}}'>
<input name='goal' placeholder='Set Funding Goal ₹'>
<button>Set Goal</button>
</form>
{% else %}
<p>Goal: ₹{{fund.goal}}</p>
<p>Raised: ₹{{fund.raised}}</p>

<div class="progress">
<div class="bar" style="width: {{ (fund.raised / fund.goal * 100) if fund.goal else 0 }}%"></div>
</div>

<form method='POST' action='/fund/{{startup.id}}'>
<input name='amount' placeholder='Add Funding ₹'>
<button>Add Funds</button>
</form>
{% endif %}

</div>
</div>
<form method='POST' action='/fund/{{startup.id}}'>
<input name='amount' placeholder='Add Funding'>
<button>Add Funds</button>
</form>
</div>

<form method='POST' action='/simulate/{{startup.id}}'>
<button>Simulate Growth</button>
</form>

<a href='/'>Back</a>

</body>
</html>
"""

# ---------------- ROUTES ----------------
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
    db.session.commit()

    db.session.add(Metrics(startup_id=s.id, visitors=10, signups=2, revenue=100))
    db.session.add(Fundraising(startup_id=s.id, goal=10000, raised=1000))
    db.session.commit()

    return redirect('/')

@app.route('/startup/<int:id>')
def startup(id):
    s = Startup.query.get(id)
    m = Metrics.query.filter_by(startup_id=id).first()
    f = Fundraising.query.filter_by(startup_id=id).first()
    ai = generate_ai(s.problem)
    return render_template_string(STARTUP_HTML, startup=s, metrics=m, fund=f, ai=ai)

@app.route('/simulate/<int:id>', methods=['POST'])
def simulate(id):
    m = Metrics.query.filter_by(startup_id=id).first()
    m.visitors += random.randint(10, 100)
    m.signups += random.randint(1, 20)
    m.revenue += random.randint(50, 500)
    db.session.commit()
    return redirect(f'/startup/{id}')

@app.route('/set_goal/<int:id>', methods=['POST'])
def set_goal(id):
    f = Fundraising.query.filter_by(startup_id=id).first()
    goal = int(request.form['goal'])
    f.goal = goal
    f.goal_set = True
    db.session.commit()
    return redirect(f'/startup/{id}')

@app.route('/fund/<int:id>', methods=['POST'])
def fund(id):
    f = Fundraising.query.filter_by(startup_id=id).first()
    amount = int(request.form['amount'])
    f.raised += amount

    # Auto-adjust goal if exceeded (smart scaling)
    if f.raised > f.goal:
        f.goal = int(f.raised * 1.5)

    db.session.commit()
    return redirect(f'/startup/{id}')

# ---------------- INIT ----------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
