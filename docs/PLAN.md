# High level steps for project

Part 1: Plan
Enrich this document to create an elaborate plan for developing the application, with substeps listed out as a checklist where each substep will be checked off after it is finished. Each usbstep should have tests and success criteria associated with it. Also create and AGENTS.md file inside the frontend directory that describes the existing code there. Ensure that the user checks and approves the plan,

Part 2: Scaffolding
Set up the backend in backend/ with FastAPI, and write the start and stop scripts in the scripts/ directory. This should serve example static HTML to confirm that a "Hello World" example works running locally and also make an API call.

Part 3: Add in Frontend
Now update so that the frontend is statically built and served, so that the app has the demo Kanban board displayed at /. Write comprehensive unit and integration tests.

Part 4: Add in a fake user sign in experience
Update so that on first hitting /, you need to log in with dummy credentials ("user","password") in order to see the Kanban board, and you can log out. Engage in writing and executing comprehensive tests.

Part 5: Database Modeling
Propose a database schema for the Kanban board, saving it as JSON. Document the database approach in docs/ and get user sign off.

Part 6: Backend
Add API routes to allow the backend to read and change the Kanban board for a given user; test this thoroughly with backend unit tests. The database should be created if it doesn't exist.

Part 7: Frontend + Backend
Now have the frontend use the backend API, so that the app provides a proper peristent Kanban board. Test very thoroughly.

Part 8: AI Connectivity
Now allow the backend to make an AI call via Groq. Test connectivity with a simple "2+2" test and ensure that the AI call is working.

Part 9: AI Call and Response
Extend the backend call to that it always calls the AI with the JSON of the Kanban board, plus the user's question (and conversation history). The AI should respond wuth Structured Outputs that includes the response to the user and optionally an update to the Kanban board. Test thoroughly.

Part 10: Add Sidebar Widget
Now add a beautiful sidebar widget to the UI supporting full AI chat, and allowing the LLM (as it decides) to udpate the Kanban board based on its Structured Outputs. If the AI updates the Kanban board, the UI should refresh automatically.