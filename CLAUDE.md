# Project Documentation & Memory Protocol

1. **Single Source of Truth**: All project architecture, rules, and current status are managed in Obsidian inside the `docs/` folder.
2. **Iterative Development (CRITICAL)**: We work strictly step-by-step. NEVER write the entire system at once. Break tasks into atomic units. Write tests or sanity checks for each component before moving to the next. Wait for my feedback before jumping to the next major phase.
3. **Read Before Act**: Before starting ANY task, you MUST read `docs/01_Architecture.md` to understand the system, and `docs/02_Current_Status.md` to know exactly what to do next.
4. **Always Update**: When completing a task, you MUST automatically update `docs/02_Current_Status.md` with what was achieved, what is pending, and any new bugs discovered. DO NOT ask for permission to update this file, just do it.
5. **Tech Stack Constraints**: Backend is pure Python/FastAPI/LangGraph. Frontend is Next.js/React/Tailwind.