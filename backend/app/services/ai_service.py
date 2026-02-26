import json
from typing import AsyncIterator, Optional
from litellm import completion

from app.config import get_settings
from app.schemas.scan import SolutionResponse
from app.utils.prompt_templates import build_solve_prompt

settings = get_settings()


class AIService:
    """
    Unified AI service using LiteLLM for multi-model support.
    
    Supported providers:
    - claude: Claude (Anthropic)
    - gpt: GPT-4 (OpenAI)
    - gemini: Gemini (Google)
    """

    MODEL_MAP = {
        "claude": "claude-3-sonnet-20240229",
        "gpt": "gpt-4o",
        "gemini": "gemini/gemini-pro",
    }

    FALLBACK_ORDER = {
        "claude": ["gpt", "gemini"],
        "gpt": ["claude", "gemini"],
        "gemini": ["gpt", "claude"],
    }

    def __init__(self):
        self._setup_api_keys()

    def _setup_api_keys(self):
        """Configure API keys for LiteLLM."""
        import os
        os.environ["ANTHROPIC_API_KEY"] = settings.anthropic_api_key or ""
        os.environ["OPENAI_API_KEY"] = settings.openai_api_key or ""
        os.environ["GEMINI_API_KEY"] = settings.google_api_key or ""

    async def solve(
        self,
        problem_text: str,
        subject: Optional[str] = "math",
        grade_level: Optional[str] = "middle school",
        provider: Optional[str] = None,
    ) -> SolutionResponse:
        """
        Generate solution for a problem using AI.
        """
        if provider == "mock" or not (settings.anthropic_api_key or settings.openai_api_key or settings.google_api_key):
             return self._mock_solve(problem_text)

        model = self._select_model(subject, provider)
        messages = self._build_prompt(problem_text, subject, grade_level)
        
        try:
            response = completion(
                model=model,
                messages=messages,
                response_format={"type": "json_object"} if "gpt" in model else None
            )
            
            content = response.choices[0].message.content
            # Clean up content if it's wrapped in triple backticks
            if content.startswith("```json"):
                content = content.replace("```json", "", 1).replace("```", "", 1).strip()
            elif content.startswith("```"):
                content = content.replace("```", "", 1).replace("```", "", 1).strip()
                
            data = json.loads(content)
            return SolutionResponse(**data)
            
        except Exception as e:
            # Fallback to mock on error for now
            return self._mock_solve(problem_text)

    def _mock_solve(self, problem_text: str) -> SolutionResponse:
        """Return a mock solution for testing."""
        return SolutionResponse(
            question_type="Linear Equation",
            knowledge_points=["Algebra", "Linear Equations", "Isolating Variables"],
            steps=[
                {
                    "step": 1,
                    "description": "Subtract 5 from both sides of the equation to isolate the term with x.",
                    "formula": "2x + 5 - 5 = 15 - 5",
                    "calculation": "2x = 10"
                },
                {
                    "step": 2,
                    "description": "Divide both sides by 2 to solve for x.",
                    "formula": "2x / 2 = 10 / 2",
                    "calculation": "x = 5"
                }
            ],
            final_answer="x = 5",
            explanation="We isolate x by performing inverse operations. First, we remove the constant term, then we remove the coefficient.",
            tips="Always check your answer by plugging it back into the original equation: 2(5) + 5 = 10 + 5 = 15. Correct!"
        )

    async def solve_stream(
        self,
        problem_text: str,
        subject: Optional[str] = "math",
        grade_level: Optional[str] = "middle school",
        provider: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """
        Stream solution generation for real-time display.
        
        Yields:
            Solution content chunks as they are generated
        """
        model = self._select_model(subject, provider)
        messages = self._build_prompt(problem_text, subject, grade_level)
        
        try:
            response = completion(
                model=model,
                messages=messages,
                stream=True
            )
            
            for chunk in response:
                content = chunk.choices[0].delta.content
                if content:
                    yield content
        except Exception:
            yield "Error generating solution."

    def _build_prompt(
        self,
        problem_text: str,
        subject: Optional[str],
        grade_level: Optional[str],
    ) -> list[dict]:
        """Build the prompt for AI model."""
        return build_solve_prompt(
            problem_text=problem_text,
            subject=subject or "math",
            grade_level=grade_level or "middle school"
        )

    def _select_model(self, subject: Optional[str], provider: Optional[str]) -> str:
        """Select the best model based on subject and preference."""
        if provider and provider in self.MODEL_MAP:
            return self.MODEL_MAP[provider]
        
        # Default model selection based on subject
        if subject in ["math", "physics"]:
            return self.MODEL_MAP["claude"]
        elif subject == "chemistry":
            return self.MODEL_MAP["gpt"]
            
        return self.MODEL_MAP.get(settings.default_ai_provider, self.MODEL_MAP["claude"])
