from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

FOLLOWUP_SYSTEM_PROMPT = """You are a patient {subject} teacher having a conversation with a {grade_level} student.
You previously helped them solve a problem. Now they have a follow-up question.
Be encouraging, clear, and educational. Use LaTeX for any formulas.
Keep responses focused and concise."""


def build_followup_messages(
    conversation_history: list[dict],
    user_message: str,
    subject: str = "math",
    grade_level: str = "middle school",
) -> list:
    messages = [
        SystemMessage(content=FOLLOWUP_SYSTEM_PROMPT.format(
            subject=subject, grade_level=grade_level
        )),
    ]
    for msg in conversation_history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))

    messages.append(HumanMessage(content=user_message))
    return messages
