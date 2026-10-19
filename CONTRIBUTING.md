# Contributing to LexiShield

Thank you for your interest in contributing to **LexiShield: Enterprise PayPal & Card Dispute Defense Engine**! We welcome bug fixes, performance optimizations, carrier connectors, and policy compliance enhancements.

---

## Code of Conduct

We are committed to providing a welcoming, inclusive, and professional environment for all contributors. Please treat everyone with respect and follow standard open-source community guidelines.

---

## Development Environment Setup

### Prerequisites
* Python 3.12+ (or 3.13)
* Docker & Docker Compose (optional, for containerized workflows)
* Git

### Local Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Sarvesha302005/LexiShield.git
   cd LexiShield
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   # On macOS/Linux:
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Verify test suite:**
   ```bash
   pytest -v --cov=src
   ```

5. **Run the local development server:**
   ```bash
   uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload
   ```
   Visit `http://127.0.0.1:8000/` in your browser.

---

## Branching & Commit Conventions

We follow git flow with atomic, semantic commits:

* **Branch Naming:**
  - `feat/<feature-name>` for new capabilities
  - `fix/<bug-description>` for bug resolutions
  - `docs/<documentation-update>` for documentation
  - `perf/<optimization>` for performance improvements
* **Commit Messages (Conventional Commits):**
  - `feat(compliance): enforce $750 signature mandate check`
  - `fix(security): resolve certificate caching edge-case`
  - `test(visa-ce3): add 2-factor technical match scenarios`
  - `docs(architecture): update sequence diagrams`

---

## Code Quality Standards

Before submitting a Pull Request, ensure your code satisfies our quality gates:

1. **Linting and Formatting:**
   ```bash
   ruff check .
   ruff format --check .
   ```
2. **Automated Testing:**
   All pull requests must include unit and integration tests covering new logic. Overall test coverage must remain **$\ge 85\%$**.
   ```bash
   pytest -v --cov=src --cov-fail-under=85
   ```
3. **Security:**
   Never commit private sandbox keys, `.env` files, or production merchant credentials.

---

## Pull Request Lifecycle

1. Open a Pull Request targeting the `main` branch.
2. Complete the standard Pull Request template checklist.
3. Verify that all automated GitHub Actions CI jobs (Linting, Multi-Python Test Matrix, Docker Smoke Test) pass.
4. Maintainers will review your submission and merge once approved.
