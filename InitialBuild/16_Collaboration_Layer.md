**Collaboration Layer (Roadmap Item 16)**  
**Goal:** Establish a comprehensive, integrated collaboration interface that enables distributed team members to interact with the AEC OS in real time and asynchronously through familiar messaging platforms (Slack, Microsoft Teams, Discord) and a lightweight web dashboard. Natural-language commands issued in chat—such as “Add a 2-hour fire-rated door at grid B-4 on level 3 for the office fit-out” or “Run validation on the latest MEP duct run and notify the engineer”—are automatically translated via the natural language parser (Item 6), executed through the Python API wrapper (Item 5), and synchronized across the version-control backbone (Item 4), visualization bridge (Item 11), and multi-user sync (Item 12). All interactions are fully traceable, auditable (Item 13), and linked to specific element folders, generating contextual threads, task assignments, and approval workflows.

**Core Architecture**  
- **Messaging Bridge:** Bot framework that listens on designated channels and routes commands to the AEC OS core.  
- **Backend API:** FastAPI service exposing endpoints for comments, tasks, reviews, and activity feeds.  
- **Storage:** SQLite (or PostgreSQL for larger teams) for structured collaboration data, with Markdown comment files stored alongside elements for git versioning.  
- **Real-Time Layer:** WebSocket support for live updates and presence indicators.  
- **Output:** Threaded comments attached to element folders, task boards, review dashboards, and automated notifications with direct Speckle/view links.

**Prerequisites (45 minutes)**  
- Completion of Roadmap Items 1–15.  
- `aecos` package installed in editable mode.  
- `pip install fastapi uvicorn sqlalchemy pydantic-settings slack-bolt discord.py teams-bot httpx` (platform-specific bot SDKs).  
- Messaging platform bot tokens and webhook URLs stored securely in `.env`.  
- Existing Speckle streams (Item 11) and git repository (Item 4) available for linking.

**Phase 1: Messaging Bridge and Command Router (Day 1)**  
Create `aecos/collaboration/bot.py`:  
```python
from slack_bolt import App
from aecos.nlp.parser import AECParser

app = App(token=os.getenv("SLACK_BOT_TOKEN"))

@app.command("/aecos")
def handle_command(ack, command, say):
    ack()
    result = AECParser().parse(command["text"])
    if result:
        perform_action(result)  # routes to generate/validate/visualize
        say(f"✅ Executed: {result.name}\nView: {result.speckle_link}")
```

Support identical syntax across Teams and Discord using their respective SDKs.

**Phase 2: Commenting and Threading System (Day 1–2)**  
Implement element-level comments stored as `comments/{timestamp}_{user}.md` inside each element folder (automatically versioned via Item 4):  
```python
def add_comment(element_path: Path, user: str, text: str, reply_to: str = None):
    comment_file = element_path / "comments" / f"{datetime.now().isoformat()}_{user}.md"
    comment_file.parent.mkdir(exist_ok=True)
    comment_file.write_text(f"**{user}** ({datetime.now()})\n\n{text}\n\nReply-to: {reply_to}")
    aecos.sync.git_manager.commit_and_push("Added collaboration comment")
```

**Phase 3: Task Assignment and Review Workflows (Day 2)**  
Define Pydantic models for tasks and reviews in `aecos/collaboration/models.py`.  
CLI and bot commands:  
```bash
aecos task assign "Review structural beam" --assignee engineer@company.com --due 2026-03-01
```
Automated approval gates integrate with Security & Audit (next item) for sign-off requirements.

**Phase 4: Activity Feed and Notifications (Day 3)**  
Extend the notifier from Item 12 with rich context:  
- @mentions trigger immediate Slack/Teams push.  
- Dashboard feed shows recent changes, open tasks, and pending reviews with one-click links to Speckle visualizations.

**Phase 5: Web Dashboard (Day 3–4)**  
Lightweight FastAPI + HTMX (or optional Streamlit) dashboard at `localhost:8000/collaboration`:  
- Browse library by discipline.  
- View element with attached comments, tasks, validation status, and live preview.  
- Real-time WebSocket updates for team presence.

**Phase 6: Cross-Platform and Revit Integration (Day 4)**  
- pyRevit ribbon button “Open Collaboration Thread” that pulls comments into Revit views.  
- Bidirectional sync: comments added in Speckle appear in the AEC OS chat.

**Phase 7: Testing, Security, and Scaling (Day 5)**  
- Multi-user simulation: 6 concurrent team members issuing commands, commenting, and approving elements.  
- Permission checks (roles from Item 13) enforced on every action.  
- Performance target: command latency < 3 seconds.  
- Full audit logging of all collaboration events.

**Total Time to Working Version 1:** 5–7 days  
**Milestone Verification:** A team member types in Slack “Add insulated concrete wall, 150 mm, 2-hour rating at location A3-B4 on level 2”, the system executes the generation and validation pipeline, posts a confirmation with Speckle link, creates a threaded discussion, assigns a review task to the structural engineer, and logs the entire interaction with cryptographic audit trail—all within seconds and fully synchronized across the repository.

This collaboration layer converts the AEC OS into a true Common Data Environment, dramatically reducing email threads, version confusion, and coordination overhead while keeping every decision contextually linked to the living model.

Implement Phases 1–3 today by registering a test Slack bot and routing one sample command. Provide any platform-specific token or routing details if needed, and I will supply the exact bot handler code.
