# resume_builder

Tailors your resume to a job using the bundled prompt (`src/resume_builder/prompt_template.txt`),
then builds a 2-page `Resume.docx` and `Resume.pdf` with the original `create_resume.py` (unchanged).

Supports **100+ LLM providers** via [LiteLLM](https://docs.litellm.ai/docs/providers) (OpenAI, Gemini, Groq, Mistral, Bedrock, etc.), plus built-in Ollama and Claude backends.

## Windows (easiest)
Double-click `run_resume.bat` and pick:
1. Local Qwen 2.5 3B - installs Ollama (winget) and downloads the model (~2 GB, once)
2. Claude API - paste your Anthropic API key (used for this run only)
3. Format only - no AI

## Command line
    pip install .                          # lightweight core (docx, reportlab, pypdf)
    pip install ".[ai]"                    # adds LiteLLM for 100+ AI providers
    tailor-resume "examples/New Resume.txt" --job-title "Senior Program Manager" --company "Acme" --jd job.txt --backend qwen   -o out --verify
    tailor-resume "examples/New Resume.txt" --job-title "Senior Program Manager" --jd job.txt --backend claude -o out --verify
    create-resume resume.txt -o out --verify        # format only

> **Why `.[ai]`?**
> The base package (`pip install .`) keeps the install minimal and fast with zero heavy dependencies for users who only format resumes or use the built-in Ollama/Claude backends. Installing with the `[ai]` extra (`pip install ".[ai]"`) pulls in `litellm` and its client libraries to unlock 100+ LLMs.

### Using LiteLLM (any provider)
    # Set the provider's API key in your environment, e.g.:
    export OPENAI_API_KEY="sk-..."
    export GEMINI_API_KEY="..."
    export GROQ_API_KEY="gsk_..."

    tailor-resume resume.txt --job-title "AI Engineer" --jd job.txt --backend litellm --model gpt-4o -o out --verify
    tailor-resume resume.txt --job-title "AI Engineer" --jd job.txt --backend litellm --model gemini/gemini-2.5-flash -o out --verify
    tailor-resume resume.txt --job-title "AI Engineer" --jd job.txt --backend litellm --model groq/llama-3.3-70b-versatile -o out --verify
    tailor-resume resume.txt --job-title "AI Engineer" --jd job.txt --backend litellm --model ollama/qwen2.5:3b -o out --verify

    # See https://docs.litellm.ai/docs/providers for all supported model strings.

Outputs in the output folder: `Resume.txt` (tailored), `Resume.docx`, `Resume.pdf`,
`Resume_report.md` (fit rating, keyword table, metric questions, LinkedIn About, bullet variations)
and `Resume_raw.txt` (the model's raw reply, for debugging).

Your input TXT must use the same layout as `examples/New Resume.txt`.
After tailoring, check the warnings: the tool flags any employer/date that differs from your original
and any `[ADD METRIC]` placeholders left for you to fill in.
