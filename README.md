# FarmaSchema

**An Agricultural Scheme Discovery & Matching Tool**

FarmaSchema helps small farmers figure out which government agricultural
schemes they're likely to be relevant for. A farmer fills in a short
profile (state, crop, land size, category, irrigation), and the tool ranks
20 real central government schemes by relevance using TF-IDF + cosine
similarity, plus a transparent rule-based explanation of *why* each scheme
was matched.

> ⚠️ **This tool provides relevance screening, not legal eligibility.**
> It never guarantees that a farmer qualifies for a scheme. Every scheme
> page tells the user to verify current official criteria before applying.

---

## 1. Project structure

```
farmaschema/
│
├── frontend/                  Plain HTML / CSS / vanilla JS — no framework
│   ├── index.html             Landing page
│   ├── dashboard.html         Farmer profile form + ranked results
│   ├── scheme.html            Browse all schemes / single scheme detail
│   ├── css/
│   │   └── style.css
│   └── js/
│       ├── app.js             Shared helpers (client id, API wrapper, toast)
│       ├── dashboard.js        Form handling + rendering ranked results
│       └── scheme.js           Browse grid + single scheme detail page
│
├── backend/
│   ├── app.py                 Flask app: REST API + serves the frontend
│   ├── recommendation.py      TF-IDF + cosine similarity + rule-based matching
│   ├── database.py            SQLite bookmarks (no personal info required)
│   ├── data/
│   │   └── schemes.json       20 real central government schemes
│   └── requirements.txt
│
├── README.md
└── .gitignore
```

**One deviation from a strict two-server setup, on purpose:** `app.py`
serves the `frontend/` folder as static files *and* the `/api/...`
endpoints, so the whole project runs from **one command in one terminal**.
`flask-cors` is still enabled, so if your team prefers to open the
frontend separately (e.g. with VS Code's "Live Server") while the backend
runs on its own port, that still works with no code changes — just update
the fetch URLs in `js/app.js` if you do this.

---

## 2. Requirements

* Python 3.9+ already installed
* Windows PowerShell (commands below are PowerShell-exact)

---

## 3. Setup (do this once)

Open PowerShell in the project's root folder (the one containing `frontend/`
and `backend/`), then:

```powershell
cd backend

# Create a virtual environment named "venv"
python -m venv venv

# Activate it
.\venv\Scripts\Activate.ps1
```

> If PowerShell blocks the activation script with an execution-policy
> error, run this once (as your normal user, not admin), then try
> activating again:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
> ```

With the venv active (your prompt will show `(venv)`), install the
dependencies:

```powershell
pip install -r requirements.txt
```

---

## 4. Running the app

Everything runs from one terminal, from inside `backend/`, with the venv active:

```powershell
python app.py
```

You should see Flask start up and print something like
`Running on http://127.0.0.1:5000`. Open that URL in your browser —
you'll see the FarmaSchema landing page. The frontend and the API are both
being served by this one process, so there is nothing else to start.

To stop the server, go back to the PowerShell window and press `Ctrl + C`.

Next time you want to run it, you only need:

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python app.py
```

---

## 5. Verifying each part works (do these in order)

**a) Test the ML recommendation logic on its own, no server needed:**

```powershell
cd backend
python recommendation.py
```

You should see a sample farmer profile followed by a ranked list of
schemes with relevance scores and matched/unknown attributes printed to
the terminal.

**b) Test the API once the server is running** (`python app.py` in one
window), open a **second** PowerShell window and run:

```powershell
curl http://127.0.0.1:5000/api/health
curl http://127.0.0.1:5000/api/schemes
curl http://127.0.0.1:5000/api/schemes/pm-kisan
```

**c) Test the full flow in the browser:**

1. Go to `http://127.0.0.1:5000/`
2. Click "Find government schemes"
3. Fill in the form (try: Karnataka, Rice, 2 acres, Small Farmer, Irrigation: Yes)
4. Click "Find matching schemes" — you should see a ranked list with
   relevance percentages and a "Why this scheme?" dropdown on each card
5. Click "View details" on any card — you should land on that scheme's
   detail page with your personal relevance score in the sidebar
6. Click the ☆ bookmark button on a card or detail page — it should turn
   into ★ and a toast should confirm it

If step (c) fails but steps (a) and (b) work, the problem is almost
certainly in the frontend JS or the browser console (open DevTools →
Console to see the real error) — not in the ML or the API.

---

## 6. How the ML pipeline works (for judges / your presentation)

1. The farmer's profile (state, district, crop, land size, category,
   irrigation, free-text details) is converted into one plain-text string,
   with the key fields repeated so they carry more weight.
2. Every scheme's description, benefits, eligibility text, states, crops
   and categories are similarly converted into one text string per scheme.
3. **TfidfVectorizer** (scikit-learn) turns all of these text strings into
   numeric vectors, weighting distinctive words (like "Karnataka" or
   "beekeeping") more heavily than common words (like "farmer" or
   "scheme").
4. **cosine_similarity** measures the angle between the farmer's vector
   and each scheme's vector — a value from 0 (unrelated) to 1 (very
   similar). This becomes the `relevance_score`.
5. **Separately**, a simple rule-based layer checks the farmer's state,
   crop, category, land size and irrigation directly against each
   scheme's stated criteria, and produces `matched_attributes` (things
   that line up) and `unknown_or_missing` (things we can't confirm — we
   never assume eligibility when information wasn't provided).
6. Schemes are ranked by `relevance_score`, and every card in the UI
   shows the score plus the plain-language reasons behind it.

This is intentionally simple (no embeddings, no deep learning) so it's
easy to explain and easy to defend under questioning.

---

## 7. API reference

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Confirms the backend is running |
| GET | `/api/schemes` | All schemes (used by the browse page) |
| GET | `/api/schemes/<id>` | One scheme's full details |
| POST | `/api/recommend` | Body: farmer profile JSON → ranked recommendations |
| POST | `/api/bookmark` | Body: `{client_id, scheme_id, action}` (`action`: `add` or `remove`) |
| GET | `/api/bookmarks?client_id=...` | All bookmarks for that browser |

---

## 8. Privacy

No Aadhaar number, phone number, bank details or password is ever
collected. Bookmarks are tied to a random `client_id` generated in the
browser's `localStorage` — not to any personal identifier.

---

## 9. Known limitations (worth mentioning proactively to judges)

* Scheme data (benefits, exact percentages, portals) reflects general,
  well-established scheme information but is **not a live feed from any
  government API** — every scheme has a `verify_note` for this reason.
* TF-IDF is a text-similarity technique, not a legal-eligibility engine —
  this is why the rule-based layer and the disclaimers exist alongside it.
* The rule-based layer is intentionally simple (state / crop / category /
  land size / irrigation) — it does not model complex real eligibility
  conditions like income ceilings or land-ownership documentation.
