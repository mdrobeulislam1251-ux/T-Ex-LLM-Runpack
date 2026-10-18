---
name: fullstack-65
description: The 65-language matrix and 65-competency engineering doctrine for the fullstack-polyglot developer and all engineering agents. Use when implementing in any programming language, porting between languages, or applying the engineering competency tiers.
---

# Fullstack-65 — Language Matrix & Engineering Competencies

## Part A — The 65-Language Matrix

The fullstack-polyglot agent implements production-grade, idiomatic code in all of these.
Idiomatic means: each language's own patterns, stdlib, error handling, and tooling — never
another language's habits transliterated.

### Systems & compiled (1–12)
1. C  2. C++  3. Rust  4. Go  5. Zig  6. Nim  7. D  8. Ada  9. Fortran  10. Assembly (x86-64)  11. Assembly (ARM64)  12. Crystal

### JVM & .NET (13–20)
13. Java  14. Kotlin  15. Scala  16. Groovy  17. Clojure  18. C#  19. F#  20. Visual Basic .NET

### Web & scripting (21–32)
21. JavaScript  22. TypeScript  23. Python  24. Ruby  25. PHP  26. Perl  27. Lua  28. CoffeeScript  29. Dart  30. Elm  31. PureScript  32. ReScript/ReasonML

### Mobile & Apple (33–36)
33. Swift  34. Objective-C  35. Kotlin (Android idioms)  36. Dart (Flutter idioms)

### Functional & academic (37–44)
37. Haskell  38. OCaml  39. Erlang  40. Elixir  41. Scheme  42. Common Lisp  43. Racket  44. Prolog

### Data, scientific & query (45–53)
45. SQL (ANSI)  46. PL/pgSQL  47. T-SQL  48. GraphQL SDL  49. R  50. Julia  51. MATLAB/Octave  52. SAS  53. Sparql

### Shell, ops & config-as-code (54–60)
54. Bash/POSIX shell  55. PowerShell  56. Awk  57. Sed  58. HCL (Terraform)  59. Nix  60. Makefile/CMake

### Frontend markup & specialized (61–65)
61. HTML5  62. CSS/Sass/Less  63. Solidity  64. VHDL/Verilog  65. WebAssembly (WAT)

**Porting rule:** when translating between languages, preserve observable behavior, port the
tests first, and prove parity by running both suites.

## Part B — The 65 Engineering Competencies

### 1–15 · Architecture & Core Systems (System Design Tier)
1. Microservices choreography & orchestration (event-driven state machines)
2. Distributed systems fault tolerance (circuit breakers & retries)
3. Domain-Driven Design bounded context enforcement
4. Monorepo structural workspace isolation
5. Event sourcing & CQRS
6. Message queue routing (RabbitMQ/Kafka)
7. Thread pool optimization & concurrency flow management
8. Memory profiling, GC tuning & leak mitigation
9. Edge computing & CDN cache invalidation
10. Connection pooling, sharding & replication topologies
11. Multi-tenant resource isolation & data leakage prevention
12. Semantic API versioning & gateway routing
13. Serverless runtime optimization
14. OS process management & system call wrapping
15. High-availability failover state sync

### 16–30 · Full-Stack Web Engineering (Implementation Tier)
16. SSR & SSG (Next.js)  17. React Server Components  18. State management engines
19. Strict TypeScript generics  20. Micro-frontends & module federation
21. WebSockets / SSE real-time streams  22. GraphQL federation & resolvers
23. Relational modeling & migrations (PostgreSQL)  24. NoSQL indexing & aggregation (MongoDB)
25. In-memory caching & eviction (Redis)  26. RESTful hypermedia & OpenAPI
27. Cross-platform desktop (Electron/Tauri)  28. Container queries, flexbox & design systems
29. Web Workers & multi-threaded clients  30. Hybrid routing & fallback boundaries

### 31–45 · DevSecOps & Data Security (Hardening Tier)
31. Key management (KMS/Vault)  32. E2E encryption at rest/transit
33. Row-level security policies  34. Zero-trust segmentation
35. OAuth2/OIDC/SAML federation  36. JWT asymmetric signing & rotation
37. OWASP Top 10 hardening  38. SAST orchestration  39. SBOM & vuln patching
40. Rate limiting & throttling  41. Audit logging & immutable trails
42. Secrets sanitization  43. CSP & CORS engineering  44. Argon2id/bcrypt hashing
45. PKI & TLS lifecycle automation

### 46–60 · QA & Testing Engineering (Verification Tier)
46. TDD red-green-refactor enforcement  47. Multi-container integration testing
48. Headless E2E (Playwright)  49. API contract testing  50. k6 load/stress profiling
51. Mutation testing  52. Coverage gatekeeping & dead code removal
53. Chaos fault injection  54. Visual regression & DOM snapshots
55. WCAG 2.1 AA accessibility testing  56. DB snapshot seeding & teardown
57. Memory-leak regression detection  58. Cross-browser compatibility verification
59. Fast-fail CI pipeline design  60. Hermetic test environments

### 61–65 · Operations & Deployment (Shipping Tier)
61. Infrastructure as Code (Terraform)  62. Multi-stage Docker optimization
63. Blue-green & canary deployments  64. Secure tunnel/mesh network provisioning
65. Automated git branching, rebase & tracking sync

## Part C — Execution guardrails (apply to ALL engineering work)

- **Zero-laziness:** fully realized, runnable code. Never truncate with
  `// rest of code here`. When editing, replace complete blocks safely.
- **TDD gate:** failing test exists before feature code; tests run before "done".
- **Fail-fast:** a failing step freezes forward progress and enters the fix loop.
- **Same-pass completeness:** types, interfaces, validation, and error boundaries ship
  in the same pass as the feature — not as a promised follow-up.
- **Stack fidelity:** default choices come from the company brain; deviations need
  cto approval and a decision-log entry.
