import unittest

from app.rag.prompts import build_messages


class SessionMemoryPromptTests(unittest.TestCase):
    def test_memory_is_injected_without_duplicating_current_user_message(self):
        messages = build_messages(
            "Vậy tôi nên tránh món nào?",
            [],
            [],
            [{"role": "assistant", "content": "Bạn bị dị ứng hải sản."}],
            table_code="T01",
            session_memory="- Tôi dị ứng hải sản",
        )

        self.assertEqual(1, sum(message["content"] == "Vậy tôi nên tránh món nào?" for message in messages))
        self.assertTrue(any("Tôi dị ứng hải sản" in message["content"] for message in messages))

    def test_empty_memory_does_not_add_memory_prompt(self):
        messages = build_messages("Gợi ý món", [], [], [], session_memory="")

        self.assertFalse(any("Ghi nhớ từ các lượt cũ hơn" in message["content"] for message in messages))


if __name__ == "__main__":
    unittest.main()
