<<<<<<< HEAD
# AgentForge AI Security Platform

AgentForge is a deployable multi-agent adversarial evaluation platform for testing the deployed OpenEMR Clinical Co-Pilot at:

`https://openemr-js46.onrender.com`

This is a separate application, not an OpenEMR fork. It continuously exercises the target with structured adversarial campaigns, records judge verdicts, creates reviewable vulnerability reports, and keeps confirmed or uncertain findings in a deterministic regression loop.

## What It Does

- Runs authorized adversarial evaluations against an allowlisted target.
- Separates responsibilities across Threat Intelligence, Orchestrator, Red Team, Judge, and Documentation agents.
- Stores agent traces, results, verdicts, and report metadata in SQLite.
- Provides a FastAPI dashboard and JSON API for reviewing findings.
- Ships with a Render web service and weekly cron job configuration.
- Defaults to a low-cost weekly cadence, with a biweekly option documented below.

## Architecture

The design follows the attached architecture model in `assets/architecture-diagram.png`.

![AgentForge architecture](assets/architecture-diagram.png)

The current implementation is intentionally provider-agnostic. If `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`, and Langfuse credentials are absent, AgentForge uses deterministic seed mutation and rubric-based judging so the harness remains runnable and reproducible. The interfaces are shaped so hosted models can be plugged into the same agent boundaries later.

## Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn agentforge.app:app --reload
```

Open `http://127.0.0.1:8000`.

Run a smoke campaign:

```bash
python -m agentforge.run_campaign --intensity smoke
```

Run tests:

```bash
pytest
```

## Deployment

The repo includes:

- `Dockerfile` for container deployment.
- `render.yaml` for a Render web service plus weekly cron.
- `TARGET_ALLOWLIST` guardrail so campaigns only run against explicitly approved targets.

The default schedule in `render.yaml` is weekly:

```yaml
schedule: "0 6 * * 1"
```

For a biweekly cadence, change the cron service to a low-frequency external trigger or use Render's scheduled job settings to run every other Monday. Weekly is recommended for this project because it gives enough signal for the assignment while keeping the default campaign budget at `$2.50`.

## Review Workflow

1. The weekly cron starts a scheduled campaign.
2. The Orchestrator chooses high-severity seed cases.
3. The Red Team Agent creates bounded variants.
4. The target client sends payload sequences to the configured Clinical Co-Pilot endpoint.
5. The Judge Agent issues `pass`, `fail`, or `partial` verdicts using versioned rubrics.
6. The Documentation Agent writes markdown reports for `fail` and `partial` cases.
7. The dashboard shows the review queue, coverage, estimated cost, and agent trace.

## Important Target Integration Note

The deployed OpenEMR URL is live, but the actual Clinical Co-Pilot chat endpoint path may differ from the default `/api/copilot/chat`. Set `TARGET_CHAT_PATH` once the deployed Co-Pilot API route is known. Until then, AgentForge records integration findings as `partial` so the test harness remains honest and reviewable.

## Repository Remote

Intended GitLab remote:

`https://labs.gauntletai.com/jayceparabellum/agentforge-ai-security-platform`

=======
# Agentforge-AI Security Platform



## Getting started

To make it easy for you to get started with GitLab, here's a list of recommended next steps.

Already a pro? Just edit this README.md and make it your own. Want to make it easy? [Use the template at the bottom](#editing-this-readme)!

## Add your files

* [Create](https://docs.gitlab.com/user/project/repository/web_editor/#create-a-file) or [upload](https://docs.gitlab.com/user/project/repository/web_editor/#upload-a-file) files
* [Add files using the command line](https://docs.gitlab.com/topics/git/add_files/#add-files-to-a-git-repository) or push an existing Git repository with the following command:

```
cd existing_repo
git remote add origin https://labs.gauntletai.com/jayceparabellum/agentforge-ai-security-platform.git
git branch -M main
git push -uf origin main
```

## Integrate with your tools

* [Set up project integrations](https://labs.gauntletai.com/jayceparabellum/agentforge-ai-security-platform/-/settings/integrations)

## Collaborate with your team

* [Invite team members and collaborators](https://docs.gitlab.com/user/project/members/)
* [Create a new merge request](https://docs.gitlab.com/user/project/merge_requests/creating_merge_requests/)
* [Automatically close issues from merge requests](https://docs.gitlab.com/user/project/issues/managing_issues/#closing-issues-automatically)
* [Enable merge request approvals](https://docs.gitlab.com/user/project/merge_requests/approvals/)
* [Set auto-merge](https://docs.gitlab.com/user/project/merge_requests/auto_merge/)

## Test and Deploy

Use the built-in continuous integration in GitLab.

* [Get started with GitLab CI/CD](https://docs.gitlab.com/ci/quick_start/)
* [Analyze your code for known vulnerabilities with Static Application Security Testing (SAST)](https://docs.gitlab.com/user/application_security/sast/)
* [Deploy to Kubernetes, Amazon EC2, or Amazon ECS using Auto Deploy](https://docs.gitlab.com/topics/autodevops/requirements/)
* [Use pull-based deployments for improved Kubernetes management](https://docs.gitlab.com/user/clusters/agent/)
* [Set up protected environments](https://docs.gitlab.com/ci/environments/protected_environments/)

***

# Editing this README

When you're ready to make this README your own, just edit this file and use the handy template below (or feel free to structure it however you want - this is just a starting point!). Thanks to [makeareadme.com](https://www.makeareadme.com/) for this template.

## Suggestions for a good README

Every project is different, so consider which of these sections apply to yours. The sections used in the template are suggestions for most open source projects. Also keep in mind that while a README can be too long and detailed, too long is better than too short. If you think your README is too long, consider utilizing another form of documentation rather than cutting out information.

## Name
Choose a self-explaining name for your project.

## Description
Let people know what your project can do specifically. Provide context and add a link to any reference visitors might be unfamiliar with. A list of Features or a Background subsection can also be added here. If there are alternatives to your project, this is a good place to list differentiating factors.

## Badges
On some READMEs, you may see small images that convey metadata, such as whether or not all the tests are passing for the project. You can use Shields to add some to your README. Many services also have instructions for adding a badge.

## Visuals
Depending on what you are making, it can be a good idea to include screenshots or even a video (you'll frequently see GIFs rather than actual videos). Tools like ttygif can help, but check out Asciinema for a more sophisticated method.

## Installation
Within a particular ecosystem, there may be a common way of installing things, such as using Yarn, NuGet, or Homebrew. However, consider the possibility that whoever is reading your README is a novice and would like more guidance. Listing specific steps helps remove ambiguity and gets people to using your project as quickly as possible. If it only runs in a specific context like a particular programming language version or operating system or has dependencies that have to be installed manually, also add a Requirements subsection.

## Usage
Use examples liberally, and show the expected output if you can. It's helpful to have inline the smallest example of usage that you can demonstrate, while providing links to more sophisticated examples if they are too long to reasonably include in the README.

## Support
Tell people where they can go to for help. It can be any combination of an issue tracker, a chat room, an email address, etc.

## Roadmap
If you have ideas for releases in the future, it is a good idea to list them in the README.

## Contributing
State if you are open to contributions and what your requirements are for accepting them.

For people who want to make changes to your project, it's helpful to have some documentation on how to get started. Perhaps there is a script that they should run or some environment variables that they need to set. Make these steps explicit. These instructions could also be useful to your future self.

You can also document commands to lint the code or run tests. These steps help to ensure high code quality and reduce the likelihood that the changes inadvertently break something. Having instructions for running tests is especially helpful if it requires external setup, such as starting a Selenium server for testing in a browser.

## Authors and acknowledgment
Show your appreciation to those who have contributed to the project.

## License
For open source projects, say how it is licensed.

## Project status
If you have run out of energy or time for your project, put a note at the top of the README saying that development has slowed down or stopped completely. Someone may choose to fork your project or volunteer to step in as a maintainer or owner, allowing your project to keep going. You can also make an explicit request for maintainers.
>>>>>>> origin/main
