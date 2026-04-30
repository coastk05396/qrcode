# QR Code Generator — Exercise

## GIF

<img width="1920" height="1080" alt="output" src="https://github.com/user-attachments/assets/0391bd06-9864-4e7c-a5ff-e8d3557f9f5f" />

## Image
<img width="480" height="500" alt="Snipaste_2026-05-01_00-50-06" src="https://github.com/user-attachments/assets/d4665fd4-3842-40ac-99e2-14ca86de69fe" />

## How to Use

1. Read `PROMPT.md`
2. Answer the Design Questions (write your answers directly in `PROMPT.md`)
3. Build the prototype:
   - **Challenge Track:** Build from scratch using `PROMPT.md` as your spec
   - **Guided Track:** Go to `scaffold/`, fill in the TODOs
4. Verify with the curl tests at the bottom of `PROMPT.md`
5. Bring your Design Questions answers to live session for discussion

## Choose Your Track

**Challenge Track** — You decide the architecture, file structure, and implementation. Any language/framework is OK (Python + FastAPI recommended). Read `PROMPT.md` to get started.

**Guided Track** — File structure and boilerplate are provided. Fill in the core logic marked with `TODO`. Go to `scaffold/` and follow the instructions below.

## Guided Track Setup

**Prerequisite:** Python 3.10 or higher

For the frontend targets and `make setup-frontend`, you also need Node.js 20+ with `npm`.

```bash
cd scaffold
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If you want one-command shortcuts from the repo root, use `make`:

```bash
make setup
make dev
```

### Files to Fill In

| File | TODO | Design Decision |
|------|------|-----------------|
| `app/token_gen.py` | `generate_token()` | How to generate unique, URL-safe short tokens |
| `app/url_validator.py` | `validate_url()` | URL normalization and malicious URL blocking |
| `app/routes.py` | `redirect()` | Cache → DB lookup → 410/404 fallback flow |

### Run and Verify

```bash
uvicorn app.main:app --reload
```

Or from the repo root:

```bash
make backend
make frontend
```

Then run the verification tests from `PROMPT.md`.

## Bonus Challenges

- Build a simple frontend (input URL → display QR code image)
- Add rate limiting to the create endpoint
- Add expiration support with automatic 410 responses
