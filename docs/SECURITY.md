# Security

Do not enter confidential, regulated, sensitive, or proprietary data into public forms. Backend API keys should be kept in environment variables when using the FastAPI backend. WordPress stores only a backend URL and optional backend API key.


## AI provider keys

Do not place Gemini/OpenAI/API provider secrets in WordPress content, public JavaScript, plugin settings exports, CSV files, or GitHub. Configure provider keys only in backend environment variables. WordPress should call the backend through the Decision Studio REST proxy.
