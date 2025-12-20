# AI Code Reviewer Bot 🤖

**An automatic assistant for code review based on Mistral AI and GitHub Webhooks**

## About the Project
This bot automatically analyzes changes in your GitHub repository and sends detailed code quality reports to chat. It leverages Mistral AI to generate professional code reviews based on structured programming principles.

### 🔧 Technologies
- **FastAPI** — Handles GitHub webhooks and processes incoming requests.
- **Mistral AI** — Generates technical code reviews with a focus on structured programming.
- **GitHub Webhooks** — Tracks repository changes in real time.
- **Loguru** — Provides logging and debugging capabilities.

### 🔍 Code Review Principles
The bot evaluates code based on the following structured programming principles:
   Principle                          | Check Example                          			  |
 |----------------------------------|-----------------------------------------------------|
 | No goto statements               | Analyzes control structures for compliance.         |
 | Function size ≤ 50 lines		      | Counts lines to enforce concise functions.  		    |
 | Single entry/exit per function   | Ensures no mid-function return statements.          |
 | Block nesting ≤ 4 levels         | Reviews if/for/while structures.          		      |

