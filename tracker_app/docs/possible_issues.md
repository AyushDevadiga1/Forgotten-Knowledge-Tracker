


# 🔴 1. Functional Correctness Issues

### Logic Errors

* Incorrect conditionals (`>=` vs `>`)
* Off-by-one errors
* Wrong loop termination
* Incorrect assumptions about sorted data
* Wrong formula or algorithm implementation
* Missing else branches
* Dead code paths
* Incorrect default values
* Floating-point precision errors
* Silent fallback behavior masking errors

### Edge Cases Not Covered

* Empty input
* Null / undefined values
* Extremely large input
* Extremely small input
* Negative values
* Duplicate values
* Unicode / special characters
* Invalid format inputs
* Corrupted files
* Partial API responses
* Timeout conditions
* Boundary dates (leap years, DST changes)

---

# 🔴 2. Input Validation & Data Integrity

* Missing schema validation
* Trusting frontend validation
* Type coercion issues
* Integer overflow
* Floating overflow
* SQL injection
* NoSQL injection
* Command injection
* Path traversal
* File upload validation missing
* MIME type spoofing
* Unsafe deserialization
* JSON parsing assumptions
* Missing required fields
* Extra unexpected fields ignored
* Invalid enum values accepted

---

# 🔴 3. Security Vulnerabilities

### Authentication

* No authentication
* Broken auth logic
* Weak password policy
* Plain-text password storage
* Missing rate limiting
* JWT not verified properly
* Expired token not checked
* Refresh token abuse

### Authorization

* Missing RBAC
* IDOR (Insecure Direct Object Reference)
* Horizontal privilege escalation
* Vertical privilege escalation
* Role checks only on frontend

### Web Security

* XSS (stored/reflected)
* CSRF
* CORS misconfiguration
* Open redirect
* Clickjacking
* Missing security headers
* Session fixation
* Session not invalidated on logout

### Infrastructure

* Secrets in repo
* Hardcoded API keys
* Public S3 buckets
* Debug mode enabled in prod
* Verbose error messages leaking stack traces
* No HTTPS enforcement

---

# 🔴 4. Performance Issues

* N+1 query problem
* Missing DB indexes
* Blocking I/O
* Memory leaks
* Large objects in memory
* Unbounded arrays
* Recursive stack overflow
* Re-render loops (frontend)
* Excessive API calls
* No caching
* Inefficient algorithms (O(n²) when O(n log n) possible)
* Not paginating large results
* Synchronous file operations in request cycle
* Thread starvation
* Connection pool exhaustion

---

# 🔴 5. Concurrency & Race Conditions

* Shared mutable state
* Missing locks
* Deadlocks
* Race conditions on writes
* Lost updates
* Double execution of transactions
* Non-idempotent API endpoints
* Duplicate job execution
* Queue not transactional
* Clock drift in distributed systems
* Missing retry logic
* Infinite retry loops
* Partial failure handling

---

# 🔴 6. Database-Level Issues

* Missing constraints
* No foreign keys
* No unique indexes
* No transactions where required
* Dirty reads
* Phantom reads
* Inconsistent isolation level
* Schema drift
* Migration rollback missing
* Improper normalization
* Over-normalization
* Cascading deletes not handled
* Orphaned records
* Data duplication
* Timezone inconsistencies

---

# 🔴 7. API Design Problems

* Inconsistent response formats
* Missing status codes
* Wrong HTTP verbs
* Non-idempotent PUT
* POST used for reads
* No versioning
* No pagination
* No filtering
* No rate limiting
* Silent failures
* Inconsistent error structure
* Leaking internal fields
* No request tracing

---

# 🔴 8. Frontend Issues

* State not synchronized
* Memory leaks (event listeners)
* Infinite re-render loops
* Uncontrolled components
* Race condition in async calls
* Optimistic update without rollback
* Accessibility missing (ARIA)
* Mobile responsiveness broken
* Broken keyboard navigation
* CSS collisions
* Dark mode broken
* Layout shift (CLS)
* Hydration mismatch (SSR apps)

---

# 🔴 9. DevOps & Deployment

* No environment separation
* Using `.env` improperly
* Missing staging
* No rollback strategy
* No health checks
* No logging
* No monitoring
* No alerting
* No backup
* No restore test
* Infrastructure not reproducible
* Manual deployment steps
* Secrets not rotated
* No rate limiting at gateway
* No autoscaling rules

---

# 🔴 10. Observability & Debuggability

* No structured logging
* No correlation IDs
* No tracing
* Logs too verbose
* Logs missing error context
* No metrics
* No dashboards
* No SLO defined
* No error aggregation (Sentry, etc.)
* Silent failure in catch blocks

---

# 🔴 11. Testing Gaps

* No unit tests
* No integration tests
* No e2e tests
* Mocking too much
* No edge case tests
* No failure simulation
* No load testing
* No fuzz testing
* No contract tests
* No regression tests
* No snapshot updates
* Tests pass but app fails (false confidence)

---

# 🔴 12. Architecture Smells

* God objects
* Circular dependencies
* Tight coupling
* No abstraction layers
* Business logic in controllers
* Massive functions
* No separation of concerns
* Inconsistent naming
* Hidden side effects
* Implicit global state
* Hardcoded config
* Magic numbers
* Feature flags unmanaged

---

# 🔴 13. AI-Specific (If AI was used to build it)

* Hallucinated library functions
* Using deprecated APIs
* Misunderstood framework patterns
* Inconsistent error handling style
* Copy-pasted StackOverflow bugs
* Generated code not understood
* Comment-code mismatch
* Incorrect assumptions about version behavior
* Model-specific edge cases ignored

---

# 🔴 14. UX & Product Logic Issues

* Confusing error messages
* No loading state
* No empty state
* No retry option
* No undo
* Unexpected destructive actions
* Form resubmission on refresh
* Back button broken
* Session timeout unclear
* Data loss on navigation

---

# 🔴 15. Compliance & Legal

* No privacy policy
* No cookie consent
* Storing PII unencrypted
* No GDPR delete flow
* Logging sensitive data
* Payment PCI violations
* Copyright violations
* License violations

---

# 🔴 16. Data Science / ML Specific (if applicable)

* Data leakage
* Train-test contamination
* No validation split
* Improper cross-validation
* Overfitting
* Underfitting
* No model monitoring
* No drift detection
* No bias evaluation
* No explainability
* No reproducibility
* Random seed not fixed
* Feature scaling mismatch
* Training-serving skew

---

# 🔴 17. Scalability Risks

* Single point of failure
* No horizontal scaling
* No stateless design
* Sticky sessions required
* Shared filesystem dependency
* Monolith with tight DB coupling
* No sharding strategy
* No partitioning
* No CDN
* No caching layer

---

# 🔴 18. Failure Mode Analysis

Ask these explicitly:

* What happens if DB goes down?
* What happens if cache goes down?
* What happens if third-party API fails?
* What happens if request takes 30 seconds?
* What happens if 10,000 users hit at once?
* What happens if deployment fails midway?
* What happens if two users edit same record?
* What happens if data is partially written?

If you don’t know the answer — that’s a risk.

---

# 🔴 19. Configuration & Environment Issues

* Hardcoded URLs
* Localhost references in prod
* Feature flags always enabled
* Debug logs in prod
* Test credentials in code
* Inconsistent environment variables
* Missing env validation

---

# 🔴 20. Maintenance & Longevity

* No documentation
* No onboarding guide
* No architecture diagram
* No dependency updates
* No version pinning
* Deprecated packages
* No CI/CD
* No code formatting
* No linting
* No commit standards

---

# 🔴 The Meta-Level Failures (Most Important)

These kill vibecoded projects more than syntax bugs:

* Code works but nobody understands it
* No one can safely modify it
* Tests exist but don't test reality
* Architecture cannot scale
* Hidden assumptions everywhere
* “It works on my machine”
* No ownership model
* No error budget thinking

---
