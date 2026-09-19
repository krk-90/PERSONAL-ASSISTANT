from llm_gateway.provider.groq_llm import get_model
from llm_gateway.provider.fallback import get_next_model


class ModelRouter:

    def __init__(self, primary_model):
        self.current_model = primary_model

    def invoke(self, messages):

        while self.current_model:

            try:
                llm = get_model(self.current_model)

                return llm.invoke(messages)

            except Exception as e:

                print(
                    f"{self.current_model} failed: {e}"
                )

                self.current_model = get_next_model(
                    self.current_model
                )

        raise RuntimeError(
            "All models failed"
        )