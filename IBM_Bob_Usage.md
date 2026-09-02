# IBM Bob Usage — HealthBridge AI

## Project
**HealthBridge AI — AI Healthcare Awareness & Access Assistant**  
Team: **RMX24**  
Developer: **Raja Babu**  
Email: **rafficial807@gmail.com**

## How IBM Bob was used

HealthBridge AI was developed and iterated using **IBM Bob** as the AI-assisted software development environment.

### 1. Project understanding and initialization
IBM Bob was used to inspect the existing HealthBridge codebase, understand the backend/frontend structure, and maintain persistent project context through `AGENTS.md`.

### 2. Planning
Bob's planning workflow was used to break the healthcare-access problem into implementation areas including:
- healthcare chat
- safety/urgency screening
- preventive-care guidance
- care navigation
- multilingual interaction
- responsible-AI constraints
- responsive user experience

### 3. Implementation
Bob's Agent workflow was used to assist with implementation and iteration across the Python/FastAPI backend and browser frontend. The project was structured around specialized healthcare workflow components such as:
- Intent Router
- Safety Guard
- Evidence Retriever
- Triage Agent
- Prevention Coach
- Care Navigator
- Language Agent
- Response Composer

### 4. Testing and debugging
Bob was used during development to run and debug the application, inspect errors, and iterate on the implementation. The final project includes a local deterministic fallback so the core demonstration remains usable when a live AI credential is not configured.

### 5. Documentation and maintainability
Project context and safety requirements are documented in `AGENTS.md` and `README.md`. The repository is publicly available so judges can inspect the implementation.

## IBM Bob features relevant to the project

The project workflow maps to Bob's built-in development modes:

- **Plan mode** — architecture and implementation planning
- **Ask mode** — codebase understanding and technical analysis
- **Agent mode** — implementation, refactoring and debugging
- **Project context / AGENTS.md** — persistent project instructions and safety rules

## Why Bob was a good fit

Healthcare AI requires more than generating text. The project contains multiple workflow steps, safety boundaries, source retrieval, user-facing controls and iterative testing. Bob's plan → inspect → implement → test workflow helped organize these pieces while keeping the codebase maintainable.

## Important honesty note

Only describe a Bob workflow as completed if it was actually performed during development. The repository should contain the Bob-related project context/documentation that corresponds to the real development history.

## References

- IBM Bob documentation: https://bob.ibm.com/docs/ide
- IBM Bob modes: https://bob.ibm.com/docs/ide/features/modes
- IBM Bob API keys: https://bob.ibm.com/docs/ide/account/api-keys
