import os

import pytest

from backend.ai import request_completion

@pytest.mark.skipif(
    os.environ.get("RUN_GROQ_CONNECTIVITY") != "1"
    or not os.environ.get("GROQ_API_KEY"),
    reason="Set RUN_GROQ_CONNECTIVITY=1 and GROQ_API_KEY to enable the live Groq check.",
)
def test_groq_connectivity_answers_arithmetic() -> None:
    answer = request_completion(
        [
            {
                "role": "user",
                "content": "What is 6 multiplied by 7? Reply with the number only.",
            }
        ]
    )

    assert "42" in answer
