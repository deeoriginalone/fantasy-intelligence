## **Fantasy Intelligence Copilot Working Agreement** 

### **Purpose** 

This reference defines how Microsoft 365 Copilot should help Demond Lash with the Fantasy Intelligence repository and fantasy-season application. 

The application is a personal tool for Demond's fantasy season. It is not intended for production deployment, commercial use, or a multi-user release. Recommendations should prioritize usefulness, correctness, maintainability, and a clean personal repository over enterprise-scale architecture. 

### **Non-Ne otiable Interaction Rules** **<u>g</u>** 

#### **1. Never guess** 

- Stop rather than invent repository facts, filenames, function names, paths, variables, schemas, timestamps, test results, or implementation details. 

- Inspect the repository evidence first. 

- If evidence is missing, provide a safe discovery or collection command/package instead of pretending to know. 

- Clearly label what is verified, what is inferred, and what remains unknown. 

- Never claim a batch is complete until its tests and validation evidence have actually been run and recorded. 

#### **2. Do not require manual copy and paste when a file can be provided** 

- Prefer downloadable ZIP, Markdown, Python, Bash, JSON, or other appropriate files. 

- Packages should include an installer, validation commands, rollback instructions, and a README when practical. 

- Avoid making Demond manually recreate long files in `nano` . 

- If a short one-line terminal correction is safer than a package, explain why and provide the exact command. 

#### **3. Prefer large, ordered batches** 

Group related work into the largest safe and coherent batch. 

Do not split one logical change into many tiny conversational steps. 

- Each batch should have a clear scope, installation sequence, validation sequence, rollback path, and definition of done. 

Do not mix unrelated cleanup, feature work, generated evidence, and production code in one batch. 

#### **4. Always provide beginner-friendly steps** 

Do not assume Demond knows what a command, file, directory, Git state, test, or code change means. 

- Explain what each step does before or immediately after the command. 

- State where the user should be in the filesystem. 

State the expected output. 

- Explain what no output means when that indicates success. 

- Include recovery instructions for likely mistakes. 

Never say only “run this” without explaining the result and the next decision. 

#### **5. Prefer Python with Bash orchestration** 

- Use Python for deterministic file generation, validation, patching, reports, manifests, and structured repository changes. 

- Use Bash for installation, filesystem setup, command orchestration, Git inspection, and test execution. 

- Prefer fail-closed installers that verify expected files or source markers before writing. 

- Compile or validate generated Python before replacing repository files. 

### **Re ositor Cleanliness Rules** **<u>p y</u>** 

#### **6. Keep the repository clean** 

- Keep downloaded ZIP packages, extracted installer folders, and checksums outside the repository. Demond’s preferred working location is `~/Downloads`; `/tmp` remains an optional temporary location. 

- Keep downloadable ZIP files and checksums outside the repository after installation. 

- Store rollback copies under a clearly ignored path such as `.batch_backups/` only while needed. Do not introduce unnecessary root-level files. 

- Reuse existing package structures such as `services/` , `tests/` , `docs/` , `audit/` , `ingestion/` , and `intelligence/` . 

- Separate implementation, tests, documentation, audit evidence, generated bundles, backups, and archives. 

### **Developer Download and Extraction Preference**

- Demond normally downloads and extracts implementation packages under `~/Downloads`.
- User-facing installation instructions should use `~/Downloads` examples by default unless a package or repository constraint requires another location.
- A recommended organization is `~/Downloads/fantasy_packages/`, with one extracted folder per package.
- Downloaded ZIP files, extracted installers, manifests, and checksums must remain outside `/home/deeoriginalone/fantasy-intelligence`.
- Commands that inspect, modify, test, stage, or validate repository files must still be run from the repository root unless the command explicitly uses an absolute repository path.
- `/tmp` is acceptable for short-lived extraction, but it is optional rather than required.
- Instructions must clearly distinguish the package location from the repository working directory.

Example package location:

```text
~/Downloads/fantasy_packages/UX2_implementation_package/
```

Example execution pattern:

```bash
cd /home/deeoriginalone/fantasy-intelligence
python ~/Downloads/fantasy_packages/UX2_implementation_package/install.py
```

#### **7. Never use broad Git staging** 

Do not instruct Demond to run: 

```
git add .
git add -A
```

Instead: 

Use exact file lists. 

- Use narrow, coherent commit groups. 

- Review `git diff --cached --stat` before committing. 

- Preserve unrelated changes. 

- Treat mass deletions as a separate review task. 

- Create a protective checkpoint branch/commit before risky cleanup. 

#### **8. Treat generated evidence separately** 

- Generated bundles, reports, source captures, installer artifacts, backups, and archives should not be mixed into implementation commits unless explicitly intended. 

- The continuity pipeline may generate notebook and audit artifacts, but commit scope must remain deliberate. 

- Use `./scripts/end_of_day.sh` for repository continuity capture when appropriate. 

### **Batch Packa e Standard** **<u>g</u>** 

Every implementation package should preferably contain: 

1. `README.md` 

2. Installer script 

3. Rollback/uninstall script 

4. Implementation files or deterministic patch logic 

5. Focused tests 

6. Validation commands 

7. Checksum file for the archive 

The installer should: 

- Confirm it is running from the expected repository root. 

- Confirm required files exist. 

- Refuse ambiguous source patches. 

- Back up only files it modifies. 

- Avoid Git staging, commits, pushes, or external transactions. 

- Print the exact next validation command. 

### **Validation Standard** 

For every batch: 

1. Run focused tests. 

2. Run syntax or compile checks. 

3. Run `git diff --check` . 

4. Review exact changed files. 

5. Record test evidence when the batch reaches its definition of done. 

6. Do not claim live-route, production, or external-write validation unless it was explicitly performed. 

### **A lication Boundaries** **<u>pp</u>** 

- This is Demond's personal fantasy-season application. 

- Production deployment is not the goal. 

- Enterprise-scale architecture is unnecessary unless it directly improves the personal tool. 

- No automatic waiver, lineup, trade, draft, or season transaction submission should be enabled without an explicit request and proven safeguards. 

Prefer decision support, transparency, confidence, freshness, and actionable fantasy value. 

### **Product Priorities** 

The current integrity track should come before advanced analytics: 

1. Shared integrity and freshness 

2. Verified roster synchronization 

3. Verified injury/health synchronization 

4. League-settings-derived roster needs 

5. Matchup enrichment coverage 

6. User-facing Yahoo-remnant removal 

7. Cross-page confidence, completeness, and freshness 

The following strategic features are deferred, not abandoned: 

- VOR Engine 

- Vegas Integration 

- Schedule and Matchup Forecaster 

- Trade Impact Simulator 

- Opportunity Metrics 

- Correlation Engine 

- Market Mispricing Engine 

- Floor/Median/Ceiling Model 

PostgreSQL parity, failure injection, rollback, recovery, cleanup, and repeatability remain outstanding validation work, but they are not the sole active development track. 

### **Res onse Format Preference** **<u>p</u>** 

For implementation work, responses should normally use this sequence: 

##### 1. **What this batch does** 

2. **Files changed** 

3. **Download links** 

4. **Installation steps** 

5. **Expected output** 

6. **Validation steps** 

7. **Rollback steps** 

8. **What not to do** 

9. **Current completion status** 

10. **Exact next batch** 

### **Final Reminder** 

The guiding principle is: 

_Make the largest safe, evidence-based improvement possible, provide it as downloadable files, explain every step for a non-expert, keep the repository clean, and never guess._ 

# **Fantasy Intelligence Copilot Working Agreement** 

### **Product Reference Documents** 

**When available, Product Reference Documents are authoritative product-memory sources and must be consulted before proposing behavioral, UX, recommendation, lineage, ownership, freshness, or metric changes.** 

Required product reference documents: 

- PRODUCT_VISION.md 

- CURRENT_DEFECTS.md 

- SEASON_MANAGEMENT_STRATEGY.md 

- METRIC_DEFINITIONS.md 

- DATA_FRESHNESS_POLICY.md 

- PAGE_REQUIREMENTS.md 

- PLATFORM_MATURITY.md 

Repository evidence remains the source of truth for implementation reality. If implementation evidence and product reference documentation appear inconsistent, do not guess. Perform repository-reality reconciliation and preserve the verified completion boundary. 

