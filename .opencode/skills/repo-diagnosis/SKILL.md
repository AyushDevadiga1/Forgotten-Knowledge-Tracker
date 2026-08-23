---
name: repo-diagnosis
description: >
  Use this skill whenever the user wants to deeply understand, audit, or diagnose a codebase or repository - 
  regardless of language, size, or domain. Triggers include: "understand this project", "find issues in my 
  repo", "diagnose my codebase", "what's wrong with this project", "audit this code", "find bottlenecks", 
  "check my architecture", "review my CI/CD", "find deprecated code", "is this scalable", "what could break", 
  "explain this project to me", or any request to inspect a folder of code. 
  
  This skill is DIAGNOSTIC ONLY - it reads, maps, and reports. It does not write, fix, refactor, 
  or generate replacement code. Use it whenever a repository path is mentioned or shared, 
  even if the user only asked a surface-level question - a full diagnosis surfaces what they could not ask.
---

# Repository Diagnosis Skill

## Purpose

Produce a complete, structured diagnosis of any software repository - mapping its architecture, 
surfacing every category of issue, and delivering a prioritised report the user can act on.

**This skill only reads. It never writes, edits, or executes application code.**

---

## Phase 0 - Orient Before You Dive

Before scanning anything, establish ground truth with two fast commands:

```bash
# 1. Get the shape of the repo
find <ROOT> -type f | sed 's|[^/]||g' | sort | uniq -c | sort -rn | head -5   # depth distribution
find <ROOT> -type f -name "*.py" -o -name "*.ts" -o -name "*.js" -o -name "*.go" \
  -o -name "*.java" -o -name "*.rs" -o -name "*.cs" | wc -l                   # rough code volume

# 2. Identify the project type immediately
ls <ROOT>                                # top-level files reveal everything
cat <ROOT>/package.json 2>/dev/null || cat <ROOT>/pyproject.toml 2>/dev/null \
  || cat <ROOT>/pom.xml 2>/dev/null || cat <ROOT>/go.mod 2>/dev/null \
  || cat <ROOT>/Cargo.toml 2>/dev/null || echo "No standard manifest found"
```

From these two commands, determine:
- **Primary language(s)**
- **Ecosystem** (Node/Python/JVM/Go/Rust/etc.)
- **Project type** (API, CLI, data pipeline, ML system, monorepo, library, etc.)
- **Approximate scale** (lines of code, file count, depth)

Use these answers to calibrate the rest of the scan. A 200-file Python monolith needs different 
attention than a 40-file Go microservice. Do not apply a one-size scan to everything.

---

## Phase 1 - Structure and Topology Mapping

Read the directory tree without touching file contents yet:

```bash
find <ROOT> -not -path '*/.git/*' -not -path '*/node_modules/*' \
  -not -path '*/__pycache__/*' -not -path '*/vendor/*' \
  -not -path '*/.venv/*' -not -path '*/dist/*' -not -path '*/build/*' \
  | sort | head -300
```

Build a mental map of:

| Signal | What to note |
|--------|-------------|
| Folder naming | Does `src/`, `lib/`, `core/`, `api/`, `services/`, `models/`, `utils/` exist and make sense? |
| Depth vs. breadth | Extremely deep trees = over-abstraction risk. Extremely flat = coupling risk. |
| God directories | Any single folder holding >30% of all files is a structure smell |
| Missing standard dirs | No `tests/`? No `docs/`? No config isolation? Note each gap |
| Monorepo signals | Multiple `package.json` / `pyproject.toml` at non-root levels |

---

## Phase 2 - Dependency and Versioning Audit

### 2a. Manifest inspection

Read **every** dependency manifest in the repo:

```bash
# Python
cat <ROOT>/requirements*.txt 2>/dev/null
cat <ROOT>/pyproject.toml 2>/dev/null
cat <ROOT>/setup.py 2>/dev/null
cat <ROOT>/Pipfile 2>/dev/null

# Node
cat <ROOT>/package.json 2>/dev/null
cat <ROOT>/package-lock.json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('packages',{})), 'locked packages')" 2>/dev/null

# JVM
cat <ROOT>/pom.xml 2>/dev/null
cat <ROOT>/build.gradle 2>/dev/null

# Go / Rust
cat <ROOT>/go.mod 2>/dev/null
cat <ROOT>/go.sum 2>/dev/null | wc -l
cat <ROOT>/Cargo.toml 2>/dev/null

# .NET
find <ROOT> -name "*.csproj" | xargs cat 2>/dev/null
```

### 2b. Deprecation flags to check

For each dependency found, flag:

- **Pinned to EOL version** - cross-check against known EOL schedules (e.g. Python 3.8 EOL Oct 2024, Node 16 EOL Sep 2023, Django 3.x EOL Dec 2024)
- **Major version lag** - dependency pinned 2+ major versions behind current
- **Known abandoned packages** - packages with no releases in 2+ years
- **Conflicting constraints** - two packages that pin incompatible versions of the same sub-dependency
- **Unpinned wildcards** - `*`, `>=X`, `^X` with no upper bound in production manifests (reproducibility risk)
- **Lock file vs. manifest drift** - lock file missing or older than manifest

### 2c. Runtime / interpreter version

```bash
cat <ROOT>/.python-version 2>/dev/null
cat <ROOT>/.nvmrc 2>/dev/null
cat <ROOT>/.node-version 2>/dev/null
cat <ROOT>/runtime.txt 2>/dev/null
grep -r "python_requires\|engines\s*:" <ROOT> --include="*.toml" --include="*.json" -l 2>/dev/null | head -5
```

Flag any runtime version that is EOL or within 6 months of EOL.

---

## Phase 3 - Code Quality and Engineering Standards

Work through each area **selectively** - read the most representative files, not everything.

### 3a. Entry points and main flows

```bash
# Find entry points
find <ROOT>/src <ROOT>/app <ROOT>/lib <ROOT> -maxdepth 2 \
  -name "main.*" -o -name "app.*" -o -name "index.*" -o -name "server.*" \
  -o -name "__main__.*" 2>/dev/null | head -10
```

Read 2-4 entry point files fully. These reveal:
- How the application bootstraps
- Dependency injection pattern (or lack thereof)
- Error handling at the top level
- Startup configuration discipline

### 3b. Error handling patterns

Search for error handling signals:

```bash
# Python - bare excepts
grep -rn "except:" <ROOT> --include="*.py" | head -20

# Python - pass in except
grep -rn -A1 "except" <ROOT> --include="*.py" | grep -E "^\s*pass$" | head -10

# JS/TS - unhandled promise rejections
grep -rn "\.catch\s*(" <ROOT> --include="*.js" --include="*.ts" | wc -l
grep -rn "async\s" <ROOT> --include="*.js" --include="*.ts" | wc -l

# Go - error ignored
grep -rn "_\s*=.*err" <ROOT> --include="*.go" | head -10

# General: TODO/FIXME/HACK in error paths
grep -rn "TODO\|FIXME\|HACK\|XXX\|BUG" <ROOT> \
  --include="*.py" --include="*.js" --include="*.ts" \
  --include="*.go" --include="*.java" --include="*.rs" \
  | wc -l
```

### 3c. Coupling and modularity

```bash
# Find circular import candidates (Python)
grep -rn "^from\s\|^import\s" <ROOT> --include="*.py" \
  | awk -F: '{print $1}' | sort | uniq -c | sort -rn | head -20

# Find files with very high import counts (JS/TS)
grep -rn "^import " <ROOT> --include="*.ts" --include="*.js" \
  | awk -F: '{print $1}' | sort | uniq -c | sort -rn | head -10

# God files - files over 500 lines
find <ROOT> -type f \( -name "*.py" -o -name "*.ts" -o -name "*.js" \
  -o -name "*.go" -o -name "*.java" \) \
  | xargs wc -l 2>/dev/null | sort -rn | head -20
```

Flag:
- Files > 500 lines as god-file candidates (read the top 50 lines to confirm)
- Any single module imported by >20% of other modules (hidden god-object)
- No clear module boundary (everything in one package / directory)

### 3d. Configuration and secrets management

```bash
# Hardcoded secrets scan (surface patterns only - do not echo values)
grep -rn "password\s*=\s*['\"].\+['\"]" <ROOT> \
  --include="*.py" --include="*.js" --include="*.ts" \
  --include="*.yaml" --include="*.yml" --include="*.json" \
  | grep -iv "placeholder\|example\|your_\|changeme\|xxx" \
  | head -10

# API key patterns
grep -rn "api_key\s*=\s*['\"][A-Za-z0-9_\-]\{10,\}['\"]" <ROOT> \
  --include="*.py" --include="*.js" --include="*.ts" | head -5

# .env files committed
find <ROOT> -name ".env" -not -path '*/.git/*' | head -5

# .gitignore existence and coverage
cat <ROOT>/.gitignore 2>/dev/null | head -40

# Config loading pattern
grep -rn "os\.environ\|process\.env\|dotenv\|config\." <ROOT> \
  --include="*.py" --include="*.js" --include="*.ts" | wc -l
```

---

## Phase 4 - Bottleneck and Performance Risk Detection

### 4a. Database and I/O patterns

```bash
# ORM N+1 risk (Django/SQLAlchemy/Sequelize)
grep -rn "\.objects\.filter\|\.query\.\|findAll\|findOne\|select_related\|prefetch_related" \
  <ROOT> --include="*.py" --include="*.js" --include="*.ts" | head -20

# Raw SQL in application code
grep -rn "execute\s*(['\"]SELECT\|cursor\.execute\|db\.query\s*(['\"]" \
  <ROOT> --include="*.py" --include="*.js" --include="*.ts" | head -10

# Missing pagination signals
grep -rn "findAll\(\|\.all()\|SELECT \* FROM" \
  <ROOT> --include="*.py" --include="*.js" --include="*.ts" | head -10

# Synchronous file I/O in async code (Node)
grep -rn "readFileSync\|writeFileSync\|existsSync" \
  <ROOT> --include="*.ts" --include="*.js" | head -10
```

### 4b. Caching and computation

```bash
# Missing caching indicators - repeated expensive calls
grep -rn "cache\|redis\|memcache\|lru_cache\|memoize" \
  <ROOT> --include="*.py" --include="*.js" --include="*.ts" | wc -l

# Nested loops in hot paths
grep -rn -B2 "for.*for\|\.map.*\.map\|\.forEach.*\.forEach" \
  <ROOT> --include="*.py" --include="*.js" --include="*.ts" | head -10
```

### 4c. Async correctness (Python / JS / Go)

```bash
# Python asyncio misuse
grep -rn "time\.sleep\|requests\." <ROOT> --include="*.py" \
  | grep -l "async def\|asyncio" 2>/dev/null | head -5

# Missing await
grep -rn "async def\|async function" <ROOT> \
  --include="*.py" --include="*.ts" --include="*.js" | wc -l

# Go goroutine leak candidates
grep -rn "go func\|go " <ROOT> --include="*.go" | wc -l
grep -rn "WaitGroup\|sync\.Once\|context\.Cancel" <ROOT> --include="*.go" | wc -l
```

---

## Phase 5 - Testing and Quality Gates

```bash
# Test existence
find <ROOT> -type d -name "test*" -o -name "*test*" -o -name "spec*" 2>/dev/null | head -10
find <ROOT> -type f -name "test_*.py" -o -name "*_test.py" \
  -o -name "*.test.ts" -o -name "*.spec.ts" \
  -o -name "*.test.js" -o -name "*_test.go" 2>/dev/null | wc -l

# Test-to-source ratio (approximate)
SOURCE=$(find <ROOT>/src <ROOT>/app <ROOT>/lib <ROOT> -maxdepth 4 \
  -name "*.py" -o -name "*.ts" -o -name "*.js" -o -name "*.go" 2>/dev/null \
  | grep -v test | wc -l)
TESTS=$(find <ROOT> -name "test_*.py" -o -name "*.test.ts" \
  -o -name "*.spec.ts" -o -name "*_test.go" 2>/dev/null | wc -l)
echo "Source files: $SOURCE | Test files: $TESTS"

# Coverage config
cat <ROOT>/.coveragerc 2>/dev/null
cat <ROOT>/jest.config.* 2>/dev/null
cat <ROOT>/pytest.ini 2>/dev/null || cat <ROOT>/pyproject.toml 2>/dev/null | grep -A10 "\[tool.pytest"

# Linting / formatting config
ls <ROOT>/.eslintrc* <ROOT>/.prettierrc* <ROOT>/mypy.ini \
  <ROOT>/.flake8 <ROOT>/ruff.toml <ROOT>/.golangci.yml 2>/dev/null
```

Flag:
- Zero test files = critical gap
- Test ratio < 0.3 (< 1 test file per 3 source files) = low coverage risk
- No coverage threshold configured = no quality gate
- No linter config = no style enforcement

---

## Phase 6 - CI/CD Pipeline Review

```bash
# Find all pipeline definitions
find <ROOT> -name "*.yml" -o -name "*.yaml" | xargs grep -l \
  "github\|gitlab-ci\|circle\|travis\|jenkins\|azure-pipelines\|buildkite" 2>/dev/null | head -10

# Read each one
find <ROOT>/.github/workflows -name "*.yml" 2>/dev/null | head -5 | xargs cat
cat <ROOT>/.gitlab-ci.yml 2>/dev/null
cat <ROOT>/.circleci/config.yml 2>/dev/null
cat <ROOT>/Jenkinsfile 2>/dev/null
```

For each pipeline, check:

| Check | Good signal | Risk signal |
|-------|-------------|-------------|
| Tests run in CI | `pytest`, `jest`, `go test` present | No test step |
| Lint in CI | Linter step present | No lint step |
| Branch protections | `on: pull_request` triggers | Only `on: push` to main |
| Secrets management | `${{ secrets.X }}` or env var injection | Hardcoded tokens in YAML |
| Docker image pinning | `image: node:20.11.0` | `image: node:latest` |
| Artifact caching | `cache:` or `actions/cache` | No caching (slow builds) |
| Deployment gate | Manual approval or review step | Direct deploy on push |
| Parallelism | Matrix or parallel jobs | Single long sequential job |

---

## Phase 7 - Scalability and Architecture Assessment

### 7a. Statefulness check

```bash
# In-memory state (crashes on restart / won't scale horizontally)
grep -rn "global\s\+\w\|module-level dict\|_cache\s*=\s*{}" \
  <ROOT> --include="*.py" | head -10

# Shared mutable state in singletons
grep -rn "class.*Singleton\|_instance\s*=\s*None\|getInstance" \
  <ROOT> --include="*.py" --include="*.ts" --include="*.java" | head -10

# Session/state stored in process memory
grep -rn "flask\.session\|app\.locals\|global\s" \
  <ROOT> --include="*.py" --include="*.ts" | head -10
```

### 7b. Hard-coded limits and magic numbers

```bash
grep -rn "limit\s*=\s*[0-9]\+\|MAX_\w*\s*=\s*[0-9]\+\|batch_size\s*=\s*[0-9]\+" \
  <ROOT> --include="*.py" --include="*.ts" --include="*.go" \
  | grep -v "test\|spec\|\.md" | head -20
```

### 7c. Queue / async worker patterns

```bash
grep -rn "celery\|rq\|sidekiq\|bull\|rabbitmq\|kafka\|pubsub\|sqs" \
  <ROOT> --include="*.py" --include="*.js" --include="*.ts" \
  --include="*.go" -l 2>/dev/null
```

If no queue system found and the repo has "heavy" operations (ML inference, file processing, 
email, external API calls), flag the missing async offload pattern as a scalability risk.

---

## Phase 8 - Security Surface Scan

```bash
# SQL injection patterns
grep -rn "f\"SELECT\|%s.*cursor\|format.*WHERE\|.format.*INSERT" \
  <ROOT> --include="*.py" | head -10

# Command injection
grep -rn "subprocess\.call\|os\.system\|exec(\|eval(" \
  <ROOT> --include="*.py" --include="*.js" --include="*.ts" \
  | grep -v "test\|spec" | head -10

# CORS misconfiguration (APIs)
grep -rn "CORS\|cors\|allow_origin\|Access-Control" \
  <ROOT> --include="*.py" --include="*.js" --include="*.ts" | head -10

# Auth bypass risks
grep -rn "if.*admin\|if.*is_staff\|@login_required\|auth\.middleware" \
  <ROOT> --include="*.py" --include="*.ts" | head -10
```

**Surface only - do not exploit, reproduce, or expand on any vulnerability found.**
Report the file and line number, and the category of risk.

---

## Phase 9 - Documentation and Maintainability

```bash
# README quality
wc -l <ROOT>/README* 2>/dev/null
head -80 <ROOT>/README.md 2>/dev/null

# Inline documentation
grep -rn '"""' <ROOT> --include="*.py" | wc -l          # Python docstrings
grep -rn "/\*\*" <ROOT> --include="*.ts" --include="*.js" | wc -l  # JSDoc

# CHANGELOG / versioning discipline
ls <ROOT>/CHANGELOG* <ROOT>/HISTORY* <ROOT>/RELEASES* 2>/dev/null

# Contribution guide
ls <ROOT>/CONTRIBUTING* <ROOT>/.github/CONTRIBUTING* 2>/dev/null
```

---

## Synthesis - The Diagnosis Report

After all phases, compose the report in this exact structure. 
**Do not write the report while still scanning. Complete all phases first.**

---

```
# Repository Diagnosis: <project-name>

## 0. Snapshot
- Language(s): ...
- Framework(s): ...
- Scale: ~X files, ~Y LOC, Z dependencies
- Type: (API / CLI / data pipeline / ML system / library / monorepo / etc.)
- Diagnosis scope: phases 0-9 completed

---

## 1. Critical Issues
[Issues that will cause failures, data loss, security breaches, or production outages]
Each issue:
- **[CATEGORY] Short title** - File/location
  What the issue is, why it matters, what breaks if unaddressed.

---

## 2. High-Priority Concerns
[Issues that will cause pain at scale, slow the team, or create technical debt that compounds]

---

## 3. Moderate Issues
[Code quality, style, and maintainability concerns that are worth fixing but won't cause immediate breakage]

---

## 4. Observations and Positives
[Things the project does well - explicit callouts of good patterns found]

---

## 5. Bottleneck Map
A short prose paragraph or diagram describing the single most likely production bottleneck 
path: e.g., "The critical path from request to DB is synchronous with no caching; 
under load, the findAll() in UserService.ts will be the first thing to fail."

---

## 6. Deprecation Timeline
Table of dependencies / runtimes that are EOL or approaching EOL:

| Package / Runtime | Pinned version | EOL date | Risk |
|-------------------|---------------|----------|------|
| ...               | ...           | ...      | ...  |

---

## 7. CI/CD Gap Summary
One-paragraph summary of what the pipeline does and does not gate - 
what could merge without being caught.

---

## 8. Scalability Ceiling
Describe the first architectural constraint the system will hit when traffic/data doubles:
stateful process, missing queue, no caching layer, synchronous DB calls, etc.

---

## 9. Recommended Priority Order
Numbered list - what to fix first, and why that ordering makes sense.
Keep to 7 items max. Ruthless prioritisation over exhaustive listing.
```

---

## Operating Constraints

**Speed over perfection.** The scan should complete before the user loses interest.  
Use `head`, `grep`, `wc -l`, and `find` to sample - not full `cat` on every file.

**One tool call per concept.** Batch related greps into one `bash_tool` call.  
Never run 15 sequential single-line greps when one compound command covers them.

**No false positives in the critical section.** If you grep-find something that looks 
like a hardcoded password but context shows it's a test fixture, it goes in Moderate - 
not Critical. Read 5 lines of context before escalating any security finding.

**Language calibration.** Not every pattern applies to every language.  
A Python `global` is a smell; a Go package-level `var` is idiomatic.  
Calibrate flags to the primary language(s) identified in Phase 0.

**No action, only diagnosis.** The output of this skill is a report. If the user 
asks you to fix something after reading the report, that is a separate task outside 
this skill. Acknowledge and switch modes.

**Completeness signal.** End the report with a single line:
> _Diagnosis complete. All 9 phases run. X critical, Y high-priority, Z moderate issues found._