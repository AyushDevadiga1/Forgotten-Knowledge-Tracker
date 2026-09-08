## Purpose

Defines how the web API authentication gate behaves, including when dev mode disables API key enforcement and how startup handles a missing key without churning the environment file.

## ADDED Requirements

### Requirement: NO_AUTH disables API key enforcement
The system SHALL treat `NO_AUTH=true` as authorization to serve the web API without an API key: every HTTP endpoint under the web API SHALL accept requests with no key, with an empty key, or with any key, and SHALL NOT return an authentication error. When `NO_AUTH` is unset or false, requests without a valid API key SHALL be rejected.

#### Scenario: Request without a key while dev mode is enabled
- **WHEN** `NO_AUTH=true` and a client calls a web API endpoint with no API key
- **THEN** the endpoint responds with its normal payload and no authentication error

#### Scenario: Request without a key while auth is enforced
- **WHEN** `NO_AUTH` is unset (or false) and a client calls a web API endpoint with no API key
- **THEN** the endpoint responds `401 Unauthorized`

#### Scenario: Health check stays reachable in both modes
- **WHEN** a client calls the health check endpoint
- **THEN** it responds `200` whether or not `NO_AUTH` is set

### Requirement: Startup does not append API keys to the environment file
The system SHALL NOT modify the environment file as a side effect of startup to persist a generated API key. Repeated boots SHALL NOT accumulate API key entries, and a boot without a configured key while `NO_AUTH=true` SHALL succeed with auth disabled.

#### Scenario: Repeated dev-mode boots do not grow the environment file
- **WHEN** the backend starts multiple times with `NO_AUTH=true` and no `API_KEY` configured
- **THEN** each start succeeds, auth stays disabled, and the environment file gains no new `API_KEY` lines

#### Scenario: Auth-enabled boot with a configured key keeps the file stable
- **WHEN** the backend starts with `API_KEY` already set and `NO_AUTH` unset
- **THEN** authentication is enforced with the configured key and the environment file is left unchanged
