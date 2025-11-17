# TalentX AI

**An Interactive AI-Driven Career Exploration & Voice Assistant Platform**  

**TalentX AI** is an immersive platform that empowers users to explore career paths, simulate day-to-day experiences, interact with AI-powered agents, and manage personal portfolios. With voice-enabled AI, 3D avatars, and real-time multi-agent chat, TalentX AI provides a hands-on way to discover and shape your career journey.

---

## Features

- **Avatar Selector:** Choose from multiple 3D avatars to represent yourself.  
- **Voice Career Copilot:** Converse with AI agents using text or voice input.  
- **Day-in-the-Life Simulation:** Simulate real-world career scenarios.  
- **Spark Hub:** Personalized space to explore tools, resources, and projects.  
- **Portfolio Management:** Save conversation history, generated content, and HTML portfolios to AWS S3.  
- **Audio Interaction:** Record and play back audio conversations with AI agents.  
- **Multi-Agent Chatbot:** Master agent routes queries to sub-agents (Profile, Skill Mapping, Career Pathway, Portfolio).  

---

## Architecture

![TalentX AI Architecture]([path_to_your_architecture_image.png](https://github.com/PalakKakani/TalentXAI/edit/main/Image/Architecture.png))  

---

## Tech Stack

| Layer                | Technology / Libraries                               |
|---------------------|------------------------------------------------------|
| **Frontend**         | Streamlit, HTML/CSS, 3D Model Viewer               |
| **Backend**          | Python, AWS Bedrock, Amazon Polly, Amazon Transcribe, DynamoDB, S3 |
| **Voice Processing** | Streamlit Mic Recorder, PyDub, Wave                 |
| **Data & Utils**     | Pandas, NumPy, SciPy, BeautifulSoup4, Requests     |

---

## Setup Instructions

Follow these steps to run TalentX AI locally:

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/talentx-ai.git
cd talentx-ai
````

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure AWS Services

TalentX AI requires AWS services:

* **S3 Bucket:** Store portfolios, voice recordings, and generated content.
* **DynamoDB Table:** Store chat history and agent state.
* **AWS Bedrock Agents:** For Multi-Agent Chatbot:

  * Create **Master Agent** and **Sub-Agents** (Profile, Skill Mapping, Career Pathway, Portfolio).
  * Configure each agent with instructions to handle its role.
## Multi-Agent Instructions

| Agent Type       | Agent Name          | Purpose / Role Description                                                                 | Example Instructions / Prompts                                                                 |
|-----------------|-------------------|--------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------|
| **Master Agent** | Master Agent       | Routes user queries to appropriate sub-agents and compiles final responses.               | - Receive user input (text/voice). <br> - Decide which sub-agent(s) to query. <br> - Aggregate and return responses. |
| **Sub-Agent**    | Profile Agent      | Handles user profile, personal info, and identity-related queries.                        | - Analyze user's profile details. <br> - Suggest career archetypes. <br> - Update profile state in DynamoDB. |
| **Sub-Agent**    | Skill Mapping Agent | Maps user's skills, strengths, and interests to potential roles and career paths.         | - Evaluate user's skills. <br> - Suggest skill improvements or roles. <br> - Return structured data to Master Agent. |
| **Sub-Agent**    | Career Pathway Agent | Suggests possible career paths, timelines, and learning steps based on user input.        | - Recommend career pathways based on profile/skills. <br> - Provide suggested milestones. |
| **Sub-Agent**    | Portfolio Agent     | Manages portfolio-related queries, generates content, and stores assets in S3.           | - Save user-generated content, conversation logs, and portfolio files. <br> - Provide links or summaries of portfolio assets. |

> ⚠️ Note: These instructions are **example prompts**. You can further refine and expand the prompts for each agent based on your specific use case. Each agent must be created separately in AWS Bedrock, and the Master Agent routes queries but does not contain the sub-agent logic itself.

> ⚠️ You must create your own AWS resources; the pre-built agents cannot be shared.

### 5. Run the App

```bash
streamlit run app.py
```

Open the URL in your terminal (usually `http://localhost:8501`) to access the platform.

